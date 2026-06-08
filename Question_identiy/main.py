from fastapi import FastAPI

from database import init_db
from year_api import router as year_router

app = FastAPI(title="Question Processing System")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(year_router)
