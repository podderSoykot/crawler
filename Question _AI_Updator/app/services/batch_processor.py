import logging

from sqlalchemy.orm import Session

from app.models.batch_model import Batch, BatchStatus
from app.models.qa_model import QAStatus, QAPair
from app.pipelines.update_pipeline import UpdatePipeline

logger = logging.getLogger(__name__)


class BatchProcessor:
    def __init__(self) -> None:
        self.pipeline = UpdatePipeline()

    def process_batch(self, db: Session, batch_id: int) -> dict:
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise ValueError(f"Batch {batch_id} not found.")

        batch.status = BatchStatus.PROCESSING
        db.commit()

        pending = (
            db.query(QAPair)
            .filter(QAPair.batch_id == batch_id, QAPair.status == QAStatus.PENDING)
            .order_by(QAPair.id)
            .all()
        )

        processed = 0
        failed = 0

        for qa in pending:
            try:
                self.pipeline.process_qa_record(db, qa.id)
                refreshed = db.query(QAPair).filter(QAPair.id == qa.id).first()
                if refreshed and refreshed.status == QAStatus.FAILED:
                    failed += 1
                else:
                    processed += 1
            except Exception as exc:
                logger.exception("Batch item failed: QA %s", qa.id)
                qa.status = QAStatus.FAILED
                qa.error_message = str(exc)
                db.commit()
                failed += 1

        batch.processed_count = (
            db.query(QAPair)
            .filter(
                QAPair.batch_id == batch_id,
                QAPair.status.notin_([QAStatus.PENDING, QAStatus.PROCESSING]),
            )
            .count()
        )
        batch.status = BatchStatus.COMPLETED if failed == 0 else BatchStatus.FAILED
        db.commit()

        return {
            "batch_id": batch_id,
            "processed": processed,
            "failed": failed,
            "total": batch.total_count,
            "status": batch.status.value,
        }
