from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.qa_model import QAStatus
from app.pipelines.update_pipeline import UpdatePipeline
from app.services.qa_service import QAService
from app.workers.tasks import process_qa_task

router = APIRouter(prefix="/qa", tags=["qa"])
qa_service = QAService()


class CreateQARequest(BaseModel):
    question: str
    original_answer: str | None = None


class ProcessQuestionRequest(BaseModel):
    question: str
    original_answer: str | None = None


@router.get("")
def list_qa(
    status: QAStatus | None = None,
    batch_id: int | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return qa_service.list_qa(db, status=status, batch_id=batch_id, skip=skip, limit=limit)


@router.get("/{qa_id}")
def get_qa(qa_id: int, db: Session = Depends(get_db)):
    item = qa_service.get_qa(db, qa_id)
    if not item:
        raise HTTPException(status_code=404, detail="Q/A not found.")
    return item


@router.post("")
def create_qa(payload: CreateQARequest, db: Session = Depends(get_db)):
    return qa_service.create_qa(
        db,
        question=payload.question,
        original_answer=payload.original_answer,
    )


@router.post("/{qa_id}/process")
def process_qa(qa_id: int, async_mode: bool = False, db: Session = Depends(get_db)):
    if async_mode:
        task = process_qa_task.delay(qa_id)
        return {"qa_id": qa_id, "task_id": task.id, "mode": "async"}

    pipeline = UpdatePipeline()
    try:
        qa = pipeline.process_qa_record(db, qa_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return qa_service.get_qa(db, qa.id)


@router.post("/process-question")
def process_question(payload: ProcessQuestionRequest):
    """Run search + crawl + answer generation without saving to DB."""
    pipeline = UpdatePipeline()
    return pipeline.process_question(payload.question, payload.original_answer)
