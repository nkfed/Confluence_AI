from fastapi import APIRouter
from src.services.tagging_service import TaggingService

router = APIRouter(prefix="/pages", tags=["tagging"])

@router.post("/{page_id}/auto-tag")
async def auto_tag_page(page_id: str, dry_run: bool = False):
    service = TaggingService()
    return await service.auto_tag_page(page_id, dry_run=dry_run)
