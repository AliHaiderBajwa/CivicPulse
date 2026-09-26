from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.deps import get_stats_service
from app.schemas import Stats
from app.services.stats_service import StatsService

router = APIRouter(prefix="/api")


@router.get(
    "/stats",
    response_model=Stats,
    operation_id="getStats",
    summary="Aggregates by category and priority",
)
def get_stats(
    response: Response,
    svc: Annotated[StatsService, Depends(get_stats_service)],
):
    data, hit = svc.get()
    response.headers["X-Cache"] = "HIT" if hit else "MISS"
    return data
