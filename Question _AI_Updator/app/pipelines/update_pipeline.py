import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.qa_model import QAStatus, QAPair
from app.pipelines.rag_pipeline import RAGPipeline
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)


class UpdatePipeline:
    """Identify a question, crawl the web, and produce an updated answer."""

    def __init__(self) -> None:
        self.rag_pipeline = RAGPipeline()
        self.ai_service = AIService()

    def process_question(
        self,
        question: str,
        original_answer: str | None = None,
    ) -> dict[str, Any]:
        rag_result = self.rag_pipeline.gather_context(question)
        ai_result = self.ai_service.generate_answer(
            question=question,
            context_text=rag_result["context_text"],
            original_answer=original_answer,
        )

        crawled_excerpt = rag_result["context_text"][:3000] if rag_result["context_text"] else None

        return {
            "question": question,
            "original_answer": original_answer,
            "crawled_answer": crawled_excerpt,
            "ai_answer": ai_result.get("answer"),
            "confidence_score": ai_result.get("confidence"),
            "sources": rag_result["sources"],
            "search_count": rag_result["search_count"],
            "crawled_count": rag_result["crawled_count"],
            "search_query": rag_result.get("search_query"),
            "error": ai_result.get("error"),
        }

    def process_qa_record(self, db: Session, qa_id: int) -> QAPair:
        qa = db.query(QAPair).filter(QAPair.id == qa_id).first()
        if not qa:
            raise ValueError(f"Q/A record {qa_id} not found.")

        qa.status = QAStatus.PROCESSING
        qa.error_message = None
        db.commit()

        try:
            result = self.process_question(qa.question, qa.original_answer)
            qa.crawled_answer = result.get("crawled_answer")
            qa.ai_answer = result.get("ai_answer")
            qa.sources = result.get("sources") or []
            qa.confidence_score = result.get("confidence_score")

            if result.get("error") or not qa.ai_answer:
                qa.status = QAStatus.FAILED
                qa.error_message = result.get("error") or "No answer generated."
            else:
                qa.status = QAStatus.TESTER_REVIEW
        except Exception as exc:
            logger.exception("Failed processing QA %s", qa_id)
            qa.status = QAStatus.FAILED
            qa.error_message = str(exc)

        db.commit()
        db.refresh(qa)
        return qa
