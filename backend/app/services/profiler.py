from dataclasses import asdict, dataclass, field
from datetime import datetime
import io
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import HTTPException, status
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Common string placeholders representing missing or invalid data
INVALID_PLACEHOLDERS = {
    "n/a",
    "na",
    "null",
    "none",
    "nil",
    "-",
    "--",
    "?",
    "nan",
    "#n/a",
    "#null!",
    "unknown",
    "",
}


def to_json_serializable(val: Any) -> Any:
    """Convert numpy/pandas types to native Python types safe for JSON serialization."""
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
    if isinstance(val, (pd.Timestamp, datetime)):
        return val.isoformat()
    if pd.isna(val):
        return None
    return str(val)


@dataclass
class ColumnProfileResult:
    column_name: str
    detected_data_type: str
    null_count: int
    null_percentage: float
    unique_count: int
    minimum: Optional[Any] = None
    maximum: Optional[Any] = None
    mean: Optional[float] = None
    median: Optional[float] = None
    sample_values: List[Any] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "column_name": self.column_name,
            "detected_data_type": self.detected_data_type,
            "null_count": self.null_count,
            "null_percentage": self.null_percentage,
            "unique_count": self.unique_count,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "mean": self.mean,
            "median": self.median,
            "sample_values": self.sample_values,
        }


@dataclass
class ProfileResult:
    row_count: int
    column_count: int
    duplicate_rows: int
    total_missing_values: int
    overall_data_quality_score: float
    columns: List[ColumnProfileResult]
    completely_empty_columns: List[str]
    high_null_columns: List[str]
    invalid_values_count: int
    completeness_score: float
    uniqueness_score: float
    validity_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": {
                "row_count": self.row_count,
                "column_count": self.column_count,
                "duplicate_rows": self.duplicate_rows,
                "total_missing_values": self.total_missing_values,
                "overall_data_quality_score": self.overall_data_quality_score,
            },
            "columns": [col.to_dict() for col in self.columns],
            "warnings": {
                "duplicate_rows_count": self.duplicate_rows,
                "completely_empty_columns": self.completely_empty_columns,
                "high_null_columns": self.high_null_columns,
                "invalid_values_count": self.invalid_values_count,
            },
            "quality_metrics": {
                "completeness_score": self.completeness_score,
                "uniqueness_score": self.uniqueness_score,
                "validity_score": self.validity_score,
                "completely_empty_columns": self.completely_empty_columns,
                "high_null_columns": self.high_null_columns,
            },
        }


class DataProfilerService:
    """Automated data profiling engine using Pandas."""

    @classmethod
    def load_dataframe(cls, file_path: Union[str, Path], file_type: str) -> pd.DataFrame:
        """Load DataFrame efficiently and safely from CSV or XLSX file.

        Raises:
            HTTPException(400): If file is malformed, unparseable, or empty.
        """
        path = Path(file_path)
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dataset file '{path.name}' does not exist on disk.",
            )

        norm_type = file_type.lower().lstrip(".")
        try:
            if norm_type == "csv":
                df = None
                for enc in ["utf-8", "latin-1"]:
                    try:
                        df = pd.read_csv(path, encoding=enc, low_memory=False)
                        break
                    except UnicodeDecodeError:
                        continue
                if df is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Unable to decode CSV file with supported encodings (UTF-8, Latin-1).",
                    )
            elif norm_type == "xlsx":
                df = pd.read_excel(path, engine="openpyxl")
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file type '{norm_type}' for profiling.",
                )

            return df

        except HTTPException:
            raise
        except pd.errors.EmptyDataError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dataset file contains no data or header rows.",
            )
        except Exception as exc:
            logger.error("Failed to parse file '%s' for profiling: %s", path.name, exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Malformed or corrupt dataset file: {str(exc)}",
            )

    @classmethod
    def infer_column_data_type(cls, series: pd.Series) -> str:
        """Infer granular and semantically meaningful data type for a Pandas Series."""
        non_null = series.dropna()
        if len(non_null) == 0:
            return "empty"

        if pd.api.types.is_bool_dtype(series):
            return "boolean"
        if pd.api.types.is_integer_dtype(series):
            return "integer"
        if pd.api.types.is_float_dtype(series):
            return "float"
        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime"

        # If object or string type, inspect values
        str_series = non_null.astype(str).str.strip()

        # Check boolean representations
        bool_match = str_series.str.lower().isin({"true", "false", "yes", "no", "t", "f", "1", "0"})
        if bool_match.all():
            return "boolean"

        # Check numeric representations
        converted_num = pd.to_numeric(str_series, errors="coerce")
        valid_num_count = converted_num.notna().sum()
        if valid_num_count / len(non_null) >= 0.90:
            valid_nums = converted_num.dropna()
            if len(valid_nums) > 0 and (valid_nums % 1 == 0).all():
                return "integer"
            return "float"

        # Check datetime representations on sample to avoid slow parsing
        sample = str_series.head(50)
        has_date_symbols = sample.str.contains(r"[-/:\sT]").any()
        if has_date_symbols:
            try:
                converted_date = pd.to_datetime(sample, errors="coerce", format="mixed")
                if converted_date.notna().sum() / len(sample) >= 0.80:
                    return "datetime"
            except Exception:
                pass

        # Categorical check (low cardinality non-numeric)
        unique_cnt = series.nunique(dropna=True)
        if unique_cnt <= 15 and (unique_cnt / max(len(non_null), 1)) <= 0.25:
            return "categorical"

        return "string"

    @classmethod
    def detect_invalid_values_in_series(cls, series: pd.Series, detected_type: str) -> int:
        """Count basic invalid values such as placeholder strings, invalid floats, or whitespace."""
        non_null = series.dropna()
        if len(non_null) == 0:
            return 0

        invalid_count = 0
        str_series = non_null.astype(str).str.strip().str.lower()

        # 1. Check for placeholder strings in text/object series
        invalid_count += int(str_series.isin(INVALID_PLACEHOLDERS).sum())

        # 2. Check for infinite values in numeric series
        if detected_type in ("integer", "float"):
            num_series = pd.to_numeric(non_null, errors="coerce")
            invalid_count += int(np.isinf(num_series).sum())

        return invalid_count

    @classmethod
    def profile_column(cls, col_name: str, series: pd.Series, total_rows: int) -> Tuple[ColumnProfileResult, int]:
        """Profile an individual column, computing metrics and sample values."""
        null_count = int(series.isna().sum())
        null_percentage = round((null_count / total_rows * 100.0), 2) if total_rows > 0 else 0.0
        unique_count = int(series.nunique(dropna=True))

        detected_type = cls.infer_column_data_type(series)
        invalid_count = cls.detect_invalid_values_in_series(series, detected_type)

        non_null = series.dropna()

        # Sample values (up to 5 distinct non-null values)
        sample_values: List[Any] = []
        if len(non_null) > 0:
            raw_samples = non_null.unique()[:5]
            sample_values = [to_json_serializable(v) for v in raw_samples]

        minimum: Optional[Any] = None
        maximum: Optional[Any] = None
        mean: Optional[float] = None
        median: Optional[float] = None

        if len(non_null) > 0:
            if detected_type in ("integer", "float"):
                num_series = pd.to_numeric(non_null, errors="coerce").dropna()
                if len(num_series) > 0:
                    minimum = to_json_serializable(num_series.min())
                    maximum = to_json_serializable(num_series.max())
                    raw_mean = num_series.mean()
                    raw_median = num_series.median()
                    mean = round(float(raw_mean), 4) if pd.notna(raw_mean) else None
                    median = round(float(raw_median), 4) if pd.notna(raw_median) else None
            elif detected_type == "datetime":
                date_series = pd.to_datetime(non_null, errors="coerce").dropna()
                if len(date_series) > 0:
                    minimum = to_json_serializable(date_series.min())
                    maximum = to_json_serializable(date_series.max())
            else:
                try:
                    str_non_null = non_null.astype(str)
                    minimum = to_json_serializable(str_non_null.min())
                    maximum = to_json_serializable(str_non_null.max())
                except Exception:
                    minimum = None
                    maximum = None

        col_result = ColumnProfileResult(
            column_name=str(col_name),
            detected_data_type=detected_type,
            null_count=null_count,
            null_percentage=null_percentage,
            unique_count=unique_count,
            minimum=minimum,
            maximum=maximum,
            mean=mean,
            median=median,
            sample_values=sample_values,
        )
        return col_result, invalid_count

    @classmethod
    def calculate_quality_score(
        cls,
        row_count: int,
        column_count: int,
        total_missing: int,
        duplicate_rows: int,
        invalid_values: int,
        completely_empty_cols: List[str],
    ) -> Tuple[float, float, float, float]:
        """Compute transparent overall data quality score (0.0 to 100.0) and component metrics."""
        total_cells = row_count * column_count
        if total_cells == 0 or row_count == 0 or column_count == 0:
            return 0.0, 0.0, 0.0, 0.0

        completeness_ratio = max(0.0, 1.0 - (total_missing / total_cells))
        uniqueness_ratio = max(0.0, 1.0 - (duplicate_rows / row_count))
        validity_ratio = max(0.0, 1.0 - (invalid_values / total_cells))

        completeness_score = round(completeness_ratio * 100.0, 2)
        uniqueness_score = round(uniqueness_ratio * 100.0, 2)
        validity_score = round(validity_ratio * 100.0, 2)

        # Empty column penalty (up to 10% deduction if entire columns are missing)
        empty_penalty = (len(completely_empty_cols) / column_count) * 10.0

        # Weighted composite: 50% Completeness, 30% Uniqueness, 20% Validity
        composite = (
            0.50 * completeness_score
            + 0.30 * uniqueness_score
            + 0.20 * validity_score
            - empty_penalty
        )
        overall_score = round(max(0.0, min(100.0, composite)), 2)

        return overall_score, completeness_score, uniqueness_score, validity_score

    @classmethod
    def profile_dataframe(cls, df: pd.DataFrame) -> ProfileResult:
        """Run comprehensive profiling on a loaded Pandas DataFrame."""
        row_count = int(len(df))
        column_count = int(len(df.columns))

        if column_count == 0 or row_count == 0:
            return ProfileResult(
                row_count=row_count,
                column_count=column_count,
                duplicate_rows=0,
                total_missing_values=0,
                overall_data_quality_score=0.0,
                columns=[],
                completely_empty_columns=[],
                high_null_columns=[],
                invalid_values_count=0,
                completeness_score=0.0,
                uniqueness_score=0.0,
                validity_score=0.0,
            )

        # 1. Dataset-level metrics
        duplicate_rows = int(df.duplicated().sum())
        total_missing_values = int(df.isna().sum().sum())

        # 2. Column-level profiling and anomaly detection
        columns_profile: List[ColumnProfileResult] = []
        completely_empty_columns: List[str] = []
        high_null_columns: List[str] = []
        total_invalid_values = 0

        for col in df.columns:
            series = df[col]
            col_prof, inv_count = cls.profile_column(str(col), series, row_count)
            columns_profile.append(col_prof)
            total_invalid_values += inv_count

            # Check if completely empty
            if col_prof.null_count == row_count:
                completely_empty_columns.append(str(col))

            # Check high-null (> 50%)
            if col_prof.null_percentage > 50.0:
                high_null_columns.append(str(col))

        # 3. Overall quality score
        quality_score, comp_score, uniq_score, val_score = cls.calculate_quality_score(
            row_count=row_count,
            column_count=column_count,
            total_missing=total_missing_values,
            duplicate_rows=duplicate_rows,
            invalid_values=total_invalid_values,
            completely_empty_cols=completely_empty_columns,
        )

        return ProfileResult(
            row_count=row_count,
            column_count=column_count,
            duplicate_rows=duplicate_rows,
            total_missing_values=total_missing_values,
            overall_data_quality_score=quality_score,
            columns=columns_profile,
            completely_empty_columns=completely_empty_columns,
            high_null_columns=high_null_columns,
            invalid_values_count=total_invalid_values,
            completeness_score=comp_score,
            uniqueness_score=uniq_score,
            validity_score=val_score,
        )

    @classmethod
    def profile_file(cls, file_path: Union[str, Path], file_type: str) -> ProfileResult:
        """Load file and profile the resulting dataset."""
        df = cls.load_dataframe(file_path, file_type)
        return cls.profile_dataframe(df)
