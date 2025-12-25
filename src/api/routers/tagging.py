from fastapi import APIRouter

router = APIRouter()

@router.get("/tagging")
def tagging_root():
    return {"message": "Tagging router placeholder"}
