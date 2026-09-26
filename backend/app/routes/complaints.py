from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.domain import Category, Priority, Status
from app.schemas import (
    Complaint,
    ComplaintCreate,
    ComplaintPage,
    Error,
    StatusUpdate,
    ValidationError,
)

router = APIRouter(prefix="/api")

_STUB = "Not implemented yet — issue #5"

_FIELD_ERRORS = {"model": ValidationError}
_NOT_FOUND = {"model": Error, "description": "No complaint with that id"}
_CONFLICT = {
    "model": Error,
    "description": "Transition not allowed from the current status",
}
_RATE_LIMITED = {
    "model": Error,
    "description": "Rate limit exceeded — see Retry-After header",
    "headers": {
        "Retry-After": {"description": "Seconds to wait", "schema": {"type": "integer"}}
    },
}


@router.post(
    "/complaints",
    response_model=Complaint,
    status_code=201,
    operation_id="createComplaint",
    summary="Validate, triage, persist",
    responses={400: _FIELD_ERRORS, 429: _RATE_LIMITED},
)
def create_complaint(body: ComplaintCreate) -> Complaint:
    raise HTTPException(status_code=501, detail=_STUB)


@router.get(
    "/complaints",
    response_model=ComplaintPage,
    operation_id="listComplaints",
    summary="Filter and paginate",
    responses={400: _FIELD_ERRORS},
)
def list_complaints(
    category: Annotated[Category | None, Query()] = None,
    priority: Annotated[Priority | None, Query()] = None,
    status: Annotated[Status | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ComplaintPage:
    raise HTTPException(status_code=501, detail=_STUB)


@router.get(
    "/complaints/{id}",
    response_model=Complaint,
    operation_id="getComplaint",
    responses={404: _NOT_FOUND},
)
def get_complaint(id: UUID) -> Complaint:
    raise HTTPException(status_code=501, detail=_STUB)


@router.patch(
    "/complaints/{id}/status",
    response_model=Complaint,
    operation_id="updateComplaintStatus",
    summary="Advance status through the state machine",
    responses={400: _FIELD_ERRORS, 404: _NOT_FOUND, 409: _CONFLICT},
)
def update_complaint_status(id: UUID, body: StatusUpdate) -> Complaint:
    raise HTTPException(status_code=501, detail=_STUB)
