import json
import logging
from typing import Any

from openai import OpenAI

from app.config import get_settings
from app.utils.prompt_templates import ANSWER_FROM_SOURCES_PROMPT, ORIGINAL_ANSWER_BLOCK

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key) if self.settings.openai_api_key else None

    def generate_answer(
        self,
        question: str,
        context_text: str,
        original_answer: str | None = None,
    ) -> dict[str, Any]:
        if not self.client:
            return self._fallback_answer(question, context_text)

        original_block = ""
        if original_answer:
            original_block = ORIGINAL_ANSWER_BLOCK.format(original_answer=original_answer)

        prompt = ANSWER_FROM_SOURCES_PROMPT.format(
            question=question,
            original_answer_block=original_block,
            sources=context_text or "No sources available.",
        )

        try:
            response = self.client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": "You return valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
            return {
                "answer": data.get("answer", "").strip(),
                "confidence": float(data.get("confidence") or 0.5),
                "key_sources": data.get("key_sources") or [],
            }
        except Exception as exc:
            logger.error("OpenAI answer generation failed: %s", exc)
            return self._fallback_answer(question, context_text)

    def _fallback_answer(self, question: str, context_text: str) -> dict[str, Any]:
        if not context_text.strip():
            return {
                "answer": "",
                "confidence": 0.0,
                "key_sources": [],
                "error": "No API keys configured or generation failed.",
            }

        excerpt = context_text[:1500]
        return {
            "answer": f"Based on crawled sources for '{question}':\n\n{excerpt}",
            "confidence": 0.3,
            "key_sources": [],
        }
