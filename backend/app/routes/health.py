from fastapi import APIRouter, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.schemas import Ready

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
def ready() -> Ready:
    raise HTTPException(status_code=501, detail="Not implemented yet — issue #5")


@router.get(
    "/metrics",
    operation_id="getMetrics",
    summary="Prometheus text exposition",
    response_class=Response,
    responses={200: {"content": {"text/plain": {"schema": {"type": "string"}}}}},
)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
