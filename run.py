import uvicorn
from settings import settings

if __name__ == "__main__":
    """Точка входу для запуску FastAPI додатка."""
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
