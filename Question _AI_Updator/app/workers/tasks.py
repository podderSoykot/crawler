from app.db.session import SessionLocal
from app.pipelines.update_pipeline import UpdatePipeline
from app.services.batch_processor import BatchProcessor
from app.workers.celery_app import celery_app


@celery_app.task(name="process_qa_task")
def process_qa_task(qa_id: int) -> dict:
    db = SessionLocal()
    try:
        pipeline = UpdatePipeline()
        qa = pipeline.process_qa_record(db, qa_id)
        return {"qa_id": qa.id, "status": qa.status.value}
    finally:
        db.close()


@celery_app.task(name="process_batch_task")
def process_batch_task(batch_id: int) -> dict:
    db = SessionLocal()
    try:
        processor = BatchProcessor()
        return processor.process_batch(db, batch_id)
    finally:
        db.close()
