from sqlalchemy.orm import Session

from app.models.qa_model import QAStatus, QAPair


def qa_to_dict(qa: QAPair) -> dict:
    return {
        "id": qa.id,
        "batch_id": qa.batch_id,
        "question": qa.question,
        "original_answer": qa.original_answer,
        "crawled_answer": qa.crawled_answer,
        "ai_answer": qa.ai_answer,
        "final_answer": qa.final_answer,
        "sources": qa.sources or [],
        "confidence_score": qa.confidence_score,
        "status": qa.status.value,
        "error_message": qa.error_message,
        "tester_notes": qa.tester_notes,
        "manager_notes": qa.manager_notes,
        "created_at": qa.created_at.isoformat() if qa.created_at else None,
        "updated_at": qa.updated_at.isoformat() if qa.updated_at else None,
    }


class QAService:
    def list_qa(
        self,
        db: Session,
        status: QAStatus | None = None,
        batch_id: int | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        query = db.query(QAPair)
        if status:
            query = query.filter(QAPair.status == status)
        if batch_id is not None:
            query = query.filter(QAPair.batch_id == batch_id)
        rows = query.order_by(QAPair.id.desc()).offset(skip).limit(limit).all()
        return [qa_to_dict(row) for row in rows]

    def get_qa(self, db: Session, qa_id: int) -> dict | None:
        qa = db.query(QAPair).filter(QAPair.id == qa_id).first()
        return qa_to_dict(qa) if qa else None

    def create_qa(
        self,
        db: Session,
        question: str,
        original_answer: str | None = None,
        batch_id: int | None = None,
    ) -> dict:
        qa = QAPair(
            question=question,
            original_answer=original_answer,
            batch_id=batch_id,
            status=QAStatus.PENDING,
        )
        db.add(qa)
        db.commit()
        db.refresh(qa)
        return qa_to_dict(qa)
