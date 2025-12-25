import logging
from fastapi import FastAPI
from src.api.routers import health, summary, tagging, bulk

# Налаштування логування
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Confluence AI Agent API")

# Підключення роутерів
app.include_router(health.router)
app.include_router(summary.router)
app.include_router(tagging.router)
app.include_router(bulk.router)

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI app initialized and starting up...")

@app.get("/")
def read_root():
    logger.info("Root endpoint called")
    return {"status": "ok", "service": "Confluence AI Agent"}
