from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.deps import get_health_service
from app.schemas import Ready, ReadyDependencies
from app.services.health_service import HealthService

router = APIRouter()


@router.get("/health", operation_id="getHealth", summary="Liveness: process is alive")
def health() -> dict[str, str]:
    # Must never touch the database — Kubernetes restarts the pod on failure.
    return {"status": "ok"}


@router.get(
    "/ready",
    response_model=Ready,
    operation_id="getReady",
    summary="Readiness: Postgres and Redis both reachable",
    responses={503: {"model": Ready, "description": "Named dependency is unreachable"}},
)
def ready(svc: Annotated[HealthService, Depends(get_health_service)]) -> Ready | JSONResponse:
    state = svc.check()
    if all(state.values()):
        return Ready(status="ok", dependencies=ReadyDependencies(**state))
    # Liveness vs readiness: a dead DB should take this pod OUT of rotation (503),
    # never RESTART it (/health does not care about the DB at all).
    return JSONResponse(status_code=503, content={"status": "degraded", "dependencies": state})


@router.get(
    "/metrics",
    operation_id="getMetrics",
    summary="Prometheus text exposition",
    response_class=Response,
    responses={200: {"content": {"text/plain": {"schema": {"type": "string"}}}}},
)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
