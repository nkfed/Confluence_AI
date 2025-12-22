import uvicorn
from settings import settings

if __name__ == "__main__":
    print("🚀 Starting FastAPI server...")
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )