from fastapi import FastAPI

# Імпорти роутерів
from src.api.routers import health, summary, tagging, bulk

app = FastAPI(
    title="Confluence AI Platform",
    version="1.0.0"
)

# Підключення роутерів
app.include_router(health.router)
app.include_router(summary.router)
app.include_router(tagging.router)
app.include_router(bulk.router)

# Головна сторінка
@app.get("/")
def root():
    return {"status": "ok", "message": "Confluence AI Platform is running"}
