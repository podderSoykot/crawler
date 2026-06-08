from sqlalchemy.orm import Session

from data_cleaner import clean_question
from database import Question


def question_to_dict(row: Question) -> dict:
    return {
        "id": row.id,
        "question": row.question,
        "clean_question": row.clean_question,
        "year": row.year,
        "is_processed": row.is_processed,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def process_questions_chunked(
    db: Session,
    chunk_size: int = 100,
    only_unprocessed: bool = True,
    year_only: bool = False,
) -> dict:
    query = db.query(Question).order_by(Question.id)
    if only_unprocessed:
        query = query.filter(Question.is_processed.is_(False))

    total_input = query.count()
    processed_count = 0
    output_count = 0
    chunks_done = 0
    offset = 0

    while True:
        batch = query.offset(offset).limit(chunk_size).all()
        if not batch:
            break

        for row in batch:
            result = clean_question(row.question)
            if result:
                row.clean_question = result["clean_question"]
                row.year = result["year"]
                if not year_only or result["year"]:
                    output_count += 1
            row.is_processed = True
            processed_count += 1

        db.commit()
        chunks_done += 1

        if only_unprocessed:
            continue
        offset += chunk_size

    return {
        "chunks_processed": chunks_done,
        "chunk_size": chunk_size,
        "input_rows": total_input,
        "processed_rows": processed_count,
        "output_rows": output_count,
    }
