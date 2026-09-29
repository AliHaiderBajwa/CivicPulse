from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.deps import get_complaint_service
from app.domain import Category, Priority, Status
from app.routes.ratelimit import enforce_rate_limit
from app.schemas import (
    Complaint,
    ComplaintCreate,
    ComplaintPage,
    Error,
    StatusUpdate,
    ValidationError,
)
from app.services.complaint_service import ComplaintService

router = APIRouter(prefix="/api")

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
    dependencies=[Depends(enforce_rate_limit)],
)
def create_complaint(
    body: ComplaintCreate,
    svc: Annotated[ComplaintService, Depends(get_complaint_service)],
):
    return svc.create(body)


@router.get(
    "/complaints",
    response_model=ComplaintPage,
    operation_id="listComplaints",
    summary="Filter and paginate",
    responses={400: _FIELD_ERRORS},
)
def list_complaints(
    svc: Annotated[ComplaintService, Depends(get_complaint_service)],
    category: Annotated[Category | None, Query()] = None,
    priority: Annotated[Priority | None, Query()] = None,
    status: Annotated[Status | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    items, total = svc.list(category=category, priority=priority, status=status,
                            page=page, page_size=page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get(
    "/complaints/{id}",
    response_model=Complaint,
    operation_id="getComplaint",
    responses={404: _NOT_FOUND},
)
def get_complaint(
    id: UUID,
    svc: Annotated[ComplaintService, Depends(get_complaint_service)],
):
    return svc.get(id)


@router.patch(
    "/complaints/{id}/status",
    response_model=Complaint,
    operation_id="updateComplaintStatus",
    summary="Advance status through the state machine",
    responses={400: _FIELD_ERRORS, 404: _NOT_FOUND, 409: _CONFLICT},
)
def update_complaint_status(
    id: UUID,
    body: StatusUpdate,
    svc: Annotated[ComplaintService, Depends(get_complaint_service)],
):
    return svc.change_status(id, body.status)
