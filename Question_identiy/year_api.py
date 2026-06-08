from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import Question, get_db
from processor import process_questions_chunked, question_to_dict

router = APIRouter(prefix="/year-questions", tags=["year-questions"])


class YearProcessRequest(BaseModel):
    chunk_size: int = Field(100, ge=1, le=1000)
    only_unprocessed: bool = True


@router.post("/process")
def process_year_questions_from_database(
    payload: YearProcessRequest,
    db: Session = Depends(get_db),
):
    """Process pending questions in chunks and keep only year-detected rows."""
    result = process_questions_chunked(
        db,
        chunk_size=payload.chunk_size,
        only_unprocessed=payload.only_unprocessed,
        year_only=True,
    )
    return {"status": "success", **result}


@router.get("")
def get_year_questions_from_database(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Return year-present questions directly from the database."""
    query = (
        db.query(Question)
        .filter(Question.is_processed.is_(True), Question.year.isnot(None))
        .order_by(Question.id.desc())
    )

    total = query.count()
    rows = query.offset(skip).limit(limit).all()

    return {
        "status": "success",
        "total_rows": total,
        "count": len(rows),
        "data": [question_to_dict(row) for row in rows],
    }
