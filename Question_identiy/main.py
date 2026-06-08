from fastapi import FastAPI
from question import router as question_router
from year_api import router as year_router

app = FastAPI(title="Question Processing System")

app.include_router(question_router)
app.include_router(year_router)