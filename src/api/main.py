from fastapi import FastAPI
from src.api.routes.summary import router as summary_router
from src.api.middleware import LoggingMiddleware
from src.core.logging.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(title="Confluence AI Agent API")
app.add_middleware(LoggingMiddleware)

logger.info("Starting API application...")

app.include_router(summary_router)

@app.get("/")
def read_root():
    logger.info("Root endpoint called")
    return {"status": "ok", "service": "Confluence AI Agent"}
