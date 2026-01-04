from fastapi import APIRouter, HTTPException
from requests.exceptions import HTTPError
from typing import Dict, Any
from src.services.summary_service import SummaryService

router = APIRouter()

@router.post("/pages/{page_id}/summary")
async def generate_page_summary(page_id: str) -> Dict[str, Any]:
    try:
        service = SummaryService()
        result = await service.summarize_page(page_id)
        return result
    except HTTPError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=404, 
                detail=f"Page with ID {page_id} not found in Confluence"
            )
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pages/{page_id}/summary-and-update")
async def generate_and_update_page_summary(page_id: str) -> Dict[str, Any]:
    try:
        service = SummaryService()
        result = await service.summarize_and_update_page(page_id)
        return result
    except PermissionError as e:
        raise HTTPException(
            status_code=403,
            detail=str(e)
        )
    except HTTPError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=404, 
                detail=f"Page with ID {page_id} not found in Confluence"
            )
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:        raise HTTPException(status_code=500, detail=str(e))