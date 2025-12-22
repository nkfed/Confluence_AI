from fastapi import FastAPI
from .routes import router

app = FastAPI(title="Confluence AI Agent API")

app.include_router(router)

@app.get("/")
def read_root():
    return {"status": "ok", "service": "Confluence AI Agent"}
