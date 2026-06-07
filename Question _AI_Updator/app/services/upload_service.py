from sqlalchemy.orm import Session

from app.models.batch_model import Batch, BatchStatus
from app.models.qa_model import QAStatus, QAPair
from app.utils.file_parser import parse_upload


class UploadService:
    def create_batch_from_upload(
        self,
        db: Session,
        filename: str,
        content: bytes,
    ) -> dict:
        records = parse_upload(filename, content)

        batch = Batch(
            filename=filename,
            total_count=len(records),
            processed_count=0,
            status=BatchStatus.UPLOADED,
        )
        db.add(batch)
        db.flush()

        for record in records:
            db.add(
                QAPair(
                    batch_id=batch.id,
                    question=record["question"],
                    original_answer=record.get("original_answer"),
                    status=QAStatus.PENDING,
                )
            )

        db.commit()
        db.refresh(batch)

        return {
            "batch_id": batch.id,
            "filename": batch.filename,
            "total_count": batch.total_count,
            "status": batch.status.value,
        }
