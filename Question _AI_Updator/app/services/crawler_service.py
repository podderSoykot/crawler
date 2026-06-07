import logging
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings

logger = logging.getLogger(__name__)


class CrawlerService:
    """Fetch and extract readable text from web pages."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def fetch_page(self, url: str) -> dict[str, Any]:
        headers = {"User-Agent": self.settings.user_agent}
        try:
            with httpx.Client(
                timeout=self.settings.crawl_timeout_seconds,
                follow_redirects=True,
                headers=headers,
            ) as client:
                response = client.get(url)
                response.raise_for_status()
                html = response.text
        except Exception as exc:
            logger.warning("Failed to crawl %s: %s", url, exc)
            return {"url": url, "content": "", "error": str(exc)}

        text = self._extract_text(html)
        return {"url": url, "content": text, "error": None}

    def crawl_urls(self, urls: list[str]) -> list[dict[str, Any]]:
        pages = []
        for url in urls:
            if not url:
                continue
            pages.append(self.fetch_page(url))
        return pages

    def _extract_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()

        main = soup.find("main") or soup.find("article") or soup.body
        if not main:
            return ""

        text = main.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:12000]
