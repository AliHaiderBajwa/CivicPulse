from fastapi import APIRouter, HTTPException, Response

from app.schemas import Stats

router = APIRouter(prefix="/api")


@router.get(
    "/stats",
    response_model=Stats,
    operation_id="getStats",
    summary="Aggregates by category and priority",
)
def get_stats(response: Response) -> Stats:
    # X-Cache: HIT|MISS is set by the cache layer (issue #6).
    raise HTTPException(status_code=501, detail="Not implemented yet — issue #6")
