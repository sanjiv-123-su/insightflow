import logging
from typing import List
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.sql_explorer import (
    SavedQueryCreate,
    SavedQueryResponse,
    SavedQueryUpdate,
    SqlQueryRequest,
    SqlQueryResponse,
)
from app.services.auth import AuthService
from app.services.sql_explorer import SqlExplorerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasets", tags=["SQL Explorer"])


@router.post(
    "/{dataset_id}/query",
    response_model=SqlQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute a read-only analytical SQL query against a dataset",
    responses={
        200: {"description": "Query executed successfully, returning table results"},
        400: {"description": "Query validation failure, disallowed mutation statement, or SQL syntax error"},
        401: {"description": "Authentication required"},
        404: {"description": "Dataset not found or access denied"},
        408: {"description": "Query execution timed out"},
        500: {"description": "Internal server error"},
    },
)
def execute_sql_query(
    dataset_id: uuid.UUID,
    request: SqlQueryRequest,
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Execute a secure, read-only analytical SQL query on an owned dataset.

    - Only authenticated users can access.
    - Strictly read-only `SELECT` statements are permitted.
    - All mutation statements (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, etc.) are blocked.
    - Stacked queries and SQL injection attempts are prevented.
    - Strict 5-second query execution timeout is enforced.
    - Output row limit is enforced (default 500, max 1000).
    - Database credentials are never exposed.
    """
    return SqlExplorerService.execute_query(
        db=db,
        user=current_user,
        dataset_id=dataset_id,
        request=request,
    )


@router.post(
    "/{dataset_id}/saved-queries",
    response_model=SavedQueryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save an analytical query for future use",
    responses={
        201: {"description": "Query saved successfully"},
        400: {"description": "Invalid query syntax or validation failure"},
        401: {"description": "Authentication required"},
        404: {"description": "Dataset not found or access denied"},
    },
)
def create_saved_query(
    dataset_id: uuid.UUID,
    data: SavedQueryCreate,
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Save an analytical SQL query associated with the specified dataset."""
    return SqlExplorerService.create_saved_query(
        db=db,
        user=current_user,
        dataset_id=dataset_id,
        data=data,
    )


@router.get(
    "/{dataset_id}/saved-queries",
    response_model=List[SavedQueryResponse],
    summary="List all saved queries for a dataset",
    responses={
        200: {"description": "List of user-saved queries for this dataset"},
        401: {"description": "Authentication required"},
        404: {"description": "Dataset not found or access denied"},
    },
)
def list_saved_queries(
    dataset_id: uuid.UUID,
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all queries saved by the authenticated user for this dataset."""
    return SqlExplorerService.list_saved_queries(
        db=db,
        user=current_user,
        dataset_id=dataset_id,
    )


@router.get(
    "/{dataset_id}/saved-queries/{query_id}",
    response_model=SavedQueryResponse,
    summary="Get a specific saved query",
    responses={
        200: {"description": "Saved query details"},
        401: {"description": "Authentication required"},
        404: {"description": "Saved query or dataset not found"},
    },
)
def get_saved_query(
    dataset_id: uuid.UUID,
    query_id: uuid.UUID,
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve an individual saved query by ID."""
    return SqlExplorerService.get_saved_query(
        db=db,
        user=current_user,
        dataset_id=dataset_id,
        query_id=query_id,
    )


@router.patch(
    "/{dataset_id}/saved-queries/{query_id}",
    response_model=SavedQueryResponse,
    summary="Update a saved query",
    responses={
        200: {"description": "Saved query updated successfully"},
        400: {"description": "Invalid query syntax"},
        401: {"description": "Authentication required"},
        404: {"description": "Saved query or dataset not found"},
    },
)
def update_saved_query(
    dataset_id: uuid.UUID,
    query_id: uuid.UUID,
    data: SavedQueryUpdate,
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Update name or SQL text for a saved query."""
    return SqlExplorerService.update_saved_query(
        db=db,
        user=current_user,
        dataset_id=dataset_id,
        query_id=query_id,
        data=data,
    )


@router.delete(
    "/{dataset_id}/saved-queries/{query_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved query",
    responses={
        204: {"description": "Saved query deleted"},
        401: {"description": "Authentication required"},
        404: {"description": "Saved query or dataset not found"},
    },
)
def delete_saved_query(
    dataset_id: uuid.UUID,
    query_id: uuid.UUID,
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a saved query permanently."""
    SqlExplorerService.delete_saved_query(
        db=db,
        user=current_user,
        dataset_id=dataset_id,
        query_id=query_id,
    )
    return None
