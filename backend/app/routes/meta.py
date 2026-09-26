from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps import get_meta_service
from app.schemas import ProviderMeta
from app.services.meta_service import MetaService

router = APIRouter(prefix="/api")


@router.get(
    "/meta/providers",
    response_model=ProviderMeta,
    operation_id="getProviderMeta",
    summary="Active triage provider and last 20 outcomes",
)
def get_provider_meta(
    svc: Annotated[MetaService, Depends(get_meta_service)],
) -> ProviderMeta:
    data = svc.providers()
    return ProviderMeta(active_provider=data["active"], recent_triages=data["recent"])
