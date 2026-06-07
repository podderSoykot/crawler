from fastapi import FastAPI

from app.api.routes import qa_routes, review_routes, upload_router
from app.config import get_settings
from app.db.session import init_db

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.include_router(upload_router.router)
app.include_router(qa_routes.router)
app.include_router(review_routes.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}
