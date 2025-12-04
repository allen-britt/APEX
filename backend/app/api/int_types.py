from fastapi import APIRouter

from app.config.int_registry import IntMetadata, get_int_registry


router = APIRouter(prefix="/int_types", tags=["int_types"])


@router.get("", response_model=list[IntMetadata])
def list_int_types() -> list[IntMetadata]:
    return get_int_registry()
