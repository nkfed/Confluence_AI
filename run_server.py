import sys
import os
import uvicorn
from settings import settings

# Додаємо src/ у PYTHONPATH, щоб імпорти api.*, services.*, agents.* працювали
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_PATH = os.path.join(BASE_DIR, "src")
if SRC_PATH not in sys.path:
    sys.path.append(SRC_PATH)

if __name__ == "__main__":
    print("Starting FastAPI server...")
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
