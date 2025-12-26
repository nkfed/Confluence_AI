from fastapi import FastAPI
from src.api.routers.health import router as health_router
from src.api.routers.summary import router as summary_router
from src.api.routers.tagging import router as tagging_router
from src.api.routers.bulk import router as bulk_router
from src.api.routers.bulk_tagging_router import router as bulk_tagging_router
from src.api.middleware import LoggingMiddleware
from src.core.logging.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(title="Confluence AI Agent API", version="0.1.0")
app.add_middleware(LoggingMiddleware)

logger.info("Starting API application...")

# Routers
app.include_router(health_router)
app.include_router(summary_router)
app.include_router(tagging_router)
app.include_router(bulk_router)
app.include_router(bulk_tagging_router)

@app.get("/")
def read_root():
    logger.info("Root endpoint called")
    return {"status": "ok", "service": "Confluence AI Agent"}