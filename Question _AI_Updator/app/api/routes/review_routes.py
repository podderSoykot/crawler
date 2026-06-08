from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.qa_model import QAStatus, QAPair
from app.services.batch_processor import BatchProcessor
from app.services.qa_service import qa_to_dict
from app.workers.tasks import process_batch_task

router = APIRouter(prefix="/review", tags=["review"])


class TesterReviewRequest(BaseModel):
    approved: bool
    notes: str | None = None
    edited_answer: str | None = None


class ManagerReviewRequest(BaseModel):
    approved: bool
    notes: str | None = None
    final_answer: str | None = None


@router.get("/tester-queue")
def tester_queue(db: Session = Depends(get_db)):
    rows = (
        db.query(QAPair)
        .filter(QAPair.status == QAStatus.TESTER_REVIEW)
        .order_by(QAPair.id)
        .all()
    )
    return [qa_to_dict(row) for row in rows]


@router.get("/manager-queue")
def manager_queue(db: Session = Depends(get_db)):
    rows = (
        db.query(QAPair)
        .filter(QAPair.status == QAStatus.MANAGER_REVIEW)
        .order_by(QAPair.id)
        .all()
    )
    return [qa_to_dict(row) for row in rows]


@router.post("/{qa_id}/tester")
def tester_review(qa_id: int, payload: TesterReviewRequest, db: Session = Depends(get_db)):
    qa = db.query(QAPair).filter(QAPair.id == qa_id).first()
    if not qa:
        raise HTTPException(status_code=404, detail="Q/A not found.")
    if qa.status != QAStatus.TESTER_REVIEW:
        raise HTTPException(status_code=400, detail="Item is not in tester review.")

    qa.tester_notes = payload.notes
    if payload.edited_answer:
        qa.ai_answer = payload.edited_answer

    if payload.approved:
        qa.status = QAStatus.MANAGER_REVIEW
    else:
        qa.status = QAStatus.REJECTED

    db.commit()
    db.refresh(qa)
    return qa_to_dict(qa)


@router.post("/{qa_id}/manager")
def manager_review(qa_id: int, payload: ManagerReviewRequest, db: Session = Depends(get_db)):
    qa = db.query(QAPair).filter(QAPair.id == qa_id).first()
    if not qa:
        raise HTTPException(status_code=404, detail="Q/A not found.")
    if qa.status != QAStatus.MANAGER_REVIEW:
        raise HTTPException(status_code=400, detail="Item is not in manager review.")

    qa.manager_notes = payload.notes

    if payload.approved:
        qa.final_answer = payload.final_answer or qa.ai_answer
        qa.status = QAStatus.APPROVED
    else:
        qa.status = QAStatus.REJECTED

    db.commit()
    db.refresh(qa)
    return qa_to_dict(qa)


@router.post("/batches/{batch_id}/process")
def process_batch(batch_id: int, async_mode: bool = True, db: Session = Depends(get_db)):
    if async_mode:
        task = process_batch_task.delay(batch_id)
        return {"batch_id": batch_id, "task_id": task.id, "mode": "async"}

    processor = BatchProcessor()
    try:
        return processor.process_batch(db, batch_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
