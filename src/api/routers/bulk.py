from fastapi import APIRouter

router = APIRouter()

@router.get("/bulk")
def bulk_root():
    return {"message": "Bulk operations router placeholder"}
