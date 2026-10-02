import concurrent.futures
from datetime import date, datetime
import logging
import math
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid

from fastapi import HTTPException, status
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.saved_query import SavedQuery
from app.models.user import User
from app.schemas.sql_explorer import (
    SavedQueryCreate,
    SavedQueryResponse,
    SavedQueryUpdate,
    SqlQueryRequest,
    SqlQueryResponse,
)
from app.services.dataset import DatasetService
from app.services.file_storage import FileStorageService
from app.services.profiler import DataProfilerService

logger = logging.getLogger(__name__)

# Maximum query execution timeout in seconds
QUERY_TIMEOUT_SECONDS = 5.0
DEFAULT_ROW_LIMIT = 500
MAX_ROW_LIMIT = 1000

# Prohibited keywords in analytical queries (must not appear outside string literals)
PROHIBITED_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "REPLACE",
    "EXEC",
    "EXECUTE",
    "PRAGMA",
    "ATTACH",
    "DETACH",
    "VACUUM",
    "INTO",
    "GRANT",
    "REVOKE",
    "TRANSACTION",
    "BEGIN",
    "COMMIT",
    "ROLLBACK",
    "LOAD_EXTENSION",
    "REINDEX",
    "SAVEPOINT",
    "RELEASE",
}

# Regex pattern matching dangerous words as distinct tokens
PROHIBITED_KEYWORD_PATTERN = re.compile(
    r"\b(" + "|".join(PROHIBITED_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

# Allowed SQLite authorizer actions during analytical execution
ALLOWED_AUTHORIZER_ACTIONS = {
    sqlite3.SQLITE_SELECT,
    sqlite3.SQLITE_READ,
    getattr(sqlite3, "SQLITE_FUNCTION", 31),
    getattr(sqlite3, "SQLITE_RECURSIVE", 33),
}


def sanitize_sql_value(val: Any) -> Any:
    """Ensure all values returned from SQLite are safe for standard JSON serialization."""
    if val is None:
        return None
    if isinstance(val, (bool, np.bool_)):
        return bool(val)
    if isinstance(val, (int, np.integer)):
        return int(val)
    if isinstance(val, (float, np.floating)):
        if math.isnan(val) or math.isinf(val):
            return None
        return float(val)
    if isinstance(val, (datetime, date, pd.Timestamp)):
        return val.isoformat()
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    if pd.isna(val):
        return None
    return val


def strip_sql_comments(sql: str) -> str:
    """Remove single-line (-- ...) and multi-line (/* ... */) comments."""
    # Remove multi-line comments
    sql_no_block = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    # Remove single-line comments
    sql_no_comments = re.sub(r"--.*$", " ", sql_no_block, flags=re.MULTILINE)
    return sql_no_comments


def strip_string_literals(sql: str) -> str:
    """Replace content inside single and double quotes with dummy placeholders to allow keyword inspection."""
    # Replace escaped quotes and content inside single quotes
    without_single_quotes = re.sub(r"'(''|[^'])*'", "''", sql)
    return without_single_quotes


def check_for_stacked_statements(sql: str) -> None:
    """Ensure that only a single SQL statement is provided (no stacked queries via semicolon)."""
    in_single_quote = False
    in_double_quote = False
    semicolon_pos = None

    i = 0
    length = len(sql)
    while i < length:
        ch = sql[i]
        if ch == "'" and not in_double_quote:
            # Handle escaping
            if i + 1 < length and sql[i + 1] == "'":
                i += 1
            else:
                in_single_quote = not in_single_quote
        elif ch == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
        elif ch == ";" and not in_single_quote and not in_double_quote:
            semicolon_pos = i
            break
        i += 1

    if semicolon_pos is not None:
        remaining = sql[semicolon_pos + 1 :].strip()
        # Strip comments from remaining to check if actual code follows
        cleaned_remaining = strip_sql_comments(remaining).strip()
        if cleaned_remaining:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multiple SQL statements (stacked queries) are strictly prohibited.",
            )


def infer_type_from_values(values: List[Any]) -> str:
    """Infer high-level column type from sample returned values."""
    for val in values:
        if val is None:
            continue
        if isinstance(val, bool):
            return "boolean"
        if isinstance(val, int):
            return "integer"
        if isinstance(val, float):
            return "float"
        if isinstance(val, (datetime, date)):
            return "datetime"
        return "string"
    return "string"


class SqlExplorerService:
    """Secure analytical SQL execution engine and saved queries management."""

    @classmethod
    def validate_query(cls, raw_query: str) -> str:
        """Thoroughly inspect and validate SQL query safety before execution.

        Checks:
        1. Non-empty string.
        2. No stacked statements or semicolons separating commands.
        3. Stripped query begins strictly with SELECT or WITH (read-only analytical CTE).
        4. No prohibited mutation / DDL keywords (DROP, DELETE, INSERT, UPDATE, etc.) outside literals.

        Returns:
            Normalized, clean query string.
        """
        if not raw_query or not raw_query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query cannot be empty.",
            )

        trimmed_query = raw_query.strip()
        if len(trimmed_query) > 10000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query length exceeds maximum limit of 10,000 characters.",
            )

        # 1. Check for multiple / stacked statements
        check_for_stacked_statements(trimmed_query)

        # 2. Strip comments to inspect underlying statement
        uncommented = strip_sql_comments(trimmed_query).strip()
        if not uncommented:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query contains only comments and no executable SQL statement.",
            )

        # 3. Verify query starts with SELECT or WITH
        first_token = uncommented.split()[0].upper()
        if first_token not in ("SELECT", "WITH"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only read-only SELECT queries are allowed. Found '{first_token}'.",
            )

        # 4. Check for prohibited mutation and administration keywords outside string literals
        clean_for_keywords = strip_string_literals(uncommented)
        prohibited_match = PROHIBITED_KEYWORD_PATTERN.search(clean_for_keywords)
        if prohibited_match:
            keyword = prohibited_match.group(0).upper()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Disallowed SQL keyword detected: '{keyword}'. Mutation and administrative statements are strictly blocked.",
            )

        return trimmed_query

    @classmethod
    def _create_sandbox_connection(
        cls,
        dataset: Dataset,
        timeout_seconds: float,
        start_time: float,
    ) -> sqlite3.Connection:
        """Create an isolated, in-memory SQLite sandbox loaded exclusively with the dataset."""
        file_path = FileStorageService.get_stored_file_path(dataset.id)
        if not file_path or not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset file not found on disk.",
            )

        # Load DataFrame from validated file
        df = DataProfilerService.load_dataframe(file_path, dataset.file_type)

        conn = sqlite3.connect(":memory:", check_same_thread=False)

        # Register dataset table
        df.to_sql("dataset", conn, if_exists="replace", index=False)

        # Create convenience aliases
        conn.execute("CREATE VIEW IF NOT EXISTS data AS SELECT * FROM dataset")

        clean_stem = re.sub(r"[^a-zA-Z0-9_]", "_", Path(dataset.original_filename).stem).lower()
        if clean_stem and clean_stem not in ("dataset", "data", "select", "from", "where", "table"):
            try:
                conn.execute(f"CREATE VIEW IF NOT EXISTS {clean_stem} AS SELECT * FROM dataset")
            except Exception:
                pass

        # Progress handler for query timeout inside SQLite virtual machine
        def progress_handler() -> int:
            if time.monotonic() - start_time > timeout_seconds:
                return 1  # Aborts execution immediately with sqlite3.OperationalError: interrupted
            return 0

        conn.set_progress_handler(progress_handler, 200)

        # SQLite Authorizer callback enforcing read-only behavior at compile time
        def security_authorizer(action: int, arg1: Any, arg2: Any, db_name: Any, trigger_name: Any) -> int:
            if action in ALLOWED_AUTHORIZER_ACTIONS:
                return sqlite3.SQLITE_OK
            logger.warning(
                "Blocked unauthorized SQLite action %s (arg1=%s, arg2=%s) on dataset %s",
                action,
                arg1,
                arg2,
                dataset.id,
            )
            return sqlite3.SQLITE_DENY

        conn.set_authorizer(security_authorizer)
        return conn

    @classmethod
    def execute_query(
        cls,
        db: Session,
        user: User,
        dataset_id: uuid.UUID,
        request: SqlQueryRequest,
    ) -> SqlQueryResponse:
        """Execute a validated, read-only analytical SQL query against the user's dataset."""
        # 1. Verify dataset ownership
        dataset = DatasetService.get_dataset(db=db, user=user, dataset_id=dataset_id)

        # 2. Validate query safety
        validated_sql = cls.validate_query(request.query)

        # 3. Calculate effective row limit
        effective_limit = min(request.limit or DEFAULT_ROW_LIMIT, MAX_ROW_LIMIT)

        start_time = time.monotonic()
        timeout_seconds = QUERY_TIMEOUT_SECONDS

        conn: Optional[sqlite3.Connection] = None
        try:
            conn = cls._create_sandbox_connection(
                dataset=dataset,
                timeout_seconds=timeout_seconds,
                start_time=start_time,
            )

            # 4. Execute query with strict timeout wrapper
            def _run_query_worker():
                cursor = conn.cursor()
                cursor.execute(validated_sql)
                # Fetch one more than limit to detect truncation
                raw_rows = cursor.fetchmany(effective_limit + 1)
                column_names = [desc[0] for desc in cursor.description] if cursor.description else []
                return column_names, raw_rows

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_run_query_worker)
                try:
                    column_names, raw_rows = future.result(timeout=timeout_seconds + 1.0)
                except concurrent.futures.TimeoutError:
                    if conn:
                        conn.interrupt()
                    raise HTTPException(
                        status_code=status.HTTP_408_REQUEST_TIMEOUT,
                        detail=f"Query execution timed out after {timeout_seconds} seconds.",
                    )

            # 5. Process results
            is_truncated = len(raw_rows) > effective_limit
            final_rows = raw_rows[:effective_limit]

            # Build JSON-serializable records
            formatted_rows: List[Dict[str, Any]] = []
            for row in final_rows:
                record = {}
                for col_name, val in zip(column_names, row):
                    record[col_name] = sanitize_sql_value(val)
                formatted_rows.append(record)

            # Inferred column types
            column_types: Dict[str, str] = {}
            for col_idx, col_name in enumerate(column_names):
                sample_col_vals = [r[col_idx] for r in final_rows[:50]]
                column_types[col_name] = infer_type_from_values(sample_col_vals)

            duration_ms = round((time.monotonic() - start_time) * 1000.0, 2)

            return SqlQueryResponse(
                dataset_id=dataset.id,
                table_name="dataset",
                columns=column_names,
                column_types=column_types,
                rows=formatted_rows,
                row_count=len(formatted_rows),
                truncated=is_truncated,
                execution_time_ms=duration_ms,
            )

        except HTTPException:
            raise

        except sqlite3.OperationalError as exc:
            err_msg = str(exc)
            if "interrupted" in err_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                    detail=f"Query execution timed out after {timeout_seconds} seconds.",
                )
            # Safe sanitized syntax error
            logger.info("SQL operational error for dataset %s: %s", dataset.id, err_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SQL Syntax/Execution Error: {err_msg}",
            )

        except sqlite3.DatabaseError as exc:
            err_msg = str(exc)
            if "not authorized" in err_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Security violation: Mutation or unauthorized operation detected. Only read-only SELECT queries are allowed.",
                )
            logger.info("SQL database error for dataset %s: %s", dataset.id, err_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SQL Database Error: {err_msg}",
            )

        except Exception as exc:
            logger.error("Unexpected error executing SQL on dataset %s: %s", dataset.id, exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal error occurred while executing the analytical query.",
            )

        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    # =========================================================================
    # Saved Queries Management
    # =========================================================================

    @classmethod
    def create_saved_query(
        cls,
        db: Session,
        user: User,
        dataset_id: uuid.UUID,
        data: SavedQueryCreate,
    ) -> SavedQuery:
        """Save a new analytical SQL query for an owned dataset."""
        # Verify ownership of dataset
        dataset = DatasetService.get_dataset(db=db, user=user, dataset_id=dataset_id)

        # Validate SQL safety
        validated_sql = cls.validate_query(data.query)

        saved = SavedQuery(
            id=uuid.uuid4(),
            user_id=user.id,
            dataset_id=dataset.id,
            name=data.name.strip(),
            query=validated_sql,
        )
        db.add(saved)
        db.commit()
        db.refresh(saved)
        return saved

    @classmethod
    def list_saved_queries(
        cls,
        db: Session,
        user: User,
        dataset_id: uuid.UUID,
    ) -> List[SavedQuery]:
        """List all saved queries belonging to the user for a specific dataset."""
        # Verify dataset ownership
        DatasetService.get_dataset(db=db, user=user, dataset_id=dataset_id)

        return (
            db.query(SavedQuery)
            .filter(
                SavedQuery.user_id == user.id,
                SavedQuery.dataset_id == dataset_id,
            )
            .order_by(SavedQuery.created_at.desc())
            .all()
        )

    @classmethod
    def get_saved_query(
        cls,
        db: Session,
        user: User,
        dataset_id: uuid.UUID,
        query_id: uuid.UUID,
    ) -> SavedQuery:
        """Retrieve a specific saved query."""
        DatasetService.get_dataset(db=db, user=user, dataset_id=dataset_id)

        saved = (
            db.query(SavedQuery)
            .filter(
                SavedQuery.id == query_id,
                SavedQuery.user_id == user.id,
                SavedQuery.dataset_id == dataset_id,
            )
            .first()
        )
        if not saved:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved query not found.",
            )
        return saved

    @classmethod
    def update_saved_query(
        cls,
        db: Session,
        user: User,
        dataset_id: uuid.UUID,
        query_id: uuid.UUID,
        data: SavedQueryUpdate,
    ) -> SavedQuery:
        """Update an existing saved query name or SQL text."""
        saved = cls.get_saved_query(db=db, user=user, dataset_id=dataset_id, query_id=query_id)

        if data.name is not None and data.name.strip():
            saved.name = data.name.strip()
        if data.query is not None and data.query.strip():
            saved.query = cls.validate_query(data.query)

        db.commit()
        db.refresh(saved)
        return saved

    @classmethod
    def delete_saved_query(
        cls,
        db: Session,
        user: User,
        dataset_id: uuid.UUID,
        query_id: uuid.UUID,
    ) -> None:
        """Delete a saved query."""
        saved = cls.get_saved_query(db=db, user=user, dataset_id=dataset_id, query_id=query_id)
        db.delete(saved)
        db.commit()
