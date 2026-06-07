import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base


class QAStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    TESTER_REVIEW = "tester_review"
    MANAGER_REVIEW = "manager_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"


class QAPair(Base):
    __tablename__ = "qa_pairs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batches.id"), nullable=True, index=True)

    question: Mapped[str] = mapped_column(Text, nullable=False)
    original_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    crawled_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_answer: Mapped[str | None] = mapped_column(Text, nullable=True)

    sources: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[QAStatus] = mapped_column(
        Enum(QAStatus), default=QAStatus.PENDING, nullable=False, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    tester_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    batch = relationship("Batch", back_populates="qa_pairs")
