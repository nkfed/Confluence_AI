from fastapi import APIRouter

router = APIRouter()

@router.post("/pages/{page_id}/summary")
def generate_page_summary(page_id: str):
    """Ендпоїнт для запуску процесу генерації summary для сторінки."""
    return {"message": f"Summary generation started for page {page_id}"}

@router.get("/health")
def health_check():
    return {"status": "healthy"}
