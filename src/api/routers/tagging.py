from fastapi import APIRouter
from src.services.tagging_service import TaggingService
from src.services.tagging_audit import TaggingAuditService

router = APIRouter(prefix="/pages", tags=["tagging"])

@router.post("/{page_id}/auto-tag")
async def auto_tag_page(page_id: str, dry_run: bool = False):
    service = TaggingService()
    return await service.auto_tag_page(page_id, dry_run=dry_run)

@router.get("/{page_id}/audit-history")
async def get_audit_history(page_id: str):
    audit = TaggingAuditService()
    return audit.get_history(page_id)
