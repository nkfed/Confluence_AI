from fastapi import FastAPI
from api.routes.summary import router as summary_router

app = FastAPI(title="Confluence AI Agent API")

app.include_router(summary_router)

@app.get("/")
def read_root():
    return {"status": "ok", "service": "Confluence AI Agent"}
