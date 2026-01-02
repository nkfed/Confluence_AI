from fastapi import APIRouter, HTTPException

from typing import Dict, Any
from src.services.summary_service import SummaryService

router = APIRouter()

@router.post("/pages/{page_id}/summary")
async def generate_page_summary(page_id: str) -> Dict[str, Any]:
    try:
        service = SummaryService()
        result = await service.summarize_page(page_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pages/{page_id}/summary-and-update")
async def generate_and_update_page_summary(page_id: str) -> Dict[str, Any]:
    try:
        service = SummaryService()
        result = await service.summarize_and_update_page(page_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
