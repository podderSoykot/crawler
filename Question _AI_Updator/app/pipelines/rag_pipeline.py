from typing import Any

from app.config import get_settings
from app.services.crawler_service import CrawlerService
from app.services.search_service import SearchService
from app.utils.search_query import build_search_query
from app.utils.source_ranker import rank_sources


class RAGPipeline:
    """Search the web, crawl top pages, and build ranked context for a question."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.search_service = SearchService()
        self.crawler_service = CrawlerService()

    def gather_context(self, question: str) -> dict[str, Any]:
        search_query = build_search_query(question)
        search_results = self.search_service.search(search_query)
        ranked = rank_sources(search_results)

        top_urls = [
            item["url"]
            for item in ranked[: self.settings.max_crawl_pages]
            if item.get("url")
        ]

        crawled_pages = self.crawler_service.crawl_urls(top_urls)
        crawled_by_url = {page["url"]: page for page in crawled_pages}

        enriched_sources: list[dict[str, Any]] = []
        for item in ranked:
            url = item.get("url", "")
            page = crawled_by_url.get(url, {})
            content = page.get("content") or item.get("snippet", "")
            enriched_sources.append(
                {
                    "title": item.get("title", ""),
                    "url": url,
                    "snippet": item.get("snippet", ""),
                    "content": content,
                    "trust_score": item.get("trust_score", 0),
                    "rank_score": item.get("rank_score", 0),
                    "crawl_error": page.get("error"),
                }
            )

        context_text = self._build_context_text(enriched_sources)
        return {
            "sources": enriched_sources,
            "context_text": context_text,
            "search_query": search_query,
            "search_count": len(search_results),
            "crawled_count": sum(1 for p in crawled_pages if p.get("content")),
        }

    def _build_context_text(self, sources: list[dict[str, Any]]) -> str:
        blocks = []
        for idx, source in enumerate(sources[: self.settings.max_crawl_pages], start=1):
            body = source.get("content") or source.get("snippet") or ""
            if not body.strip():
                continue
            blocks.append(
                f"[Source {idx}] {source.get('title', 'Untitled')}\n"
                f"URL: {source.get('url', '')}\n"
                f"Trust: {source.get('trust_score', 0)}\n"
                f"{body[:4000]}"
            )
        return "\n\n---\n\n".join(blocks)
