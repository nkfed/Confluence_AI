import sys
import os
import uvicorn
from settings import settings

# Додаємо кореневу директорію проєкту в sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Prevent uvicorn autostart during pytest/testing
if __name__ == "__main__" and os.getenv("DISABLE_UVICORN_AUTOSTART") != "1":
    print("Starting FastAPI server...")
    uvicorn.run(
        "src.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )