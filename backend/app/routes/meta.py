from fastapi import APIRouter, HTTPException

from app.schemas import ProviderMeta

router = APIRouter(prefix="/api")


@router.get(
    "/meta/providers",
    response_model=ProviderMeta,
    operation_id="getProviderMeta",
    summary="Active triage provider and last 20 outcomes",
)
def get_provider_meta() -> ProviderMeta:
    raise HTTPException(status_code=501, detail="Not implemented yet — issue #4")
