import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class SearchService:
    """Fetch web search results via Tavily (preferred) or SerpAPI."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def search(self, query: str, max_results: int | None = None) -> list[dict[str, Any]]:
        limit = max_results or self.settings.max_search_results
        if self.settings.tavily_api_key:
            results = self._search_tavily(query, limit)
            if results:
                return results

        if self.settings.serpapi_api_key:
            results = self._search_serpapi(query, limit)
            if results:
                return results

        return self._search_duckduckgo(query, limit)

    def _search_duckduckgo(self, query: str, max_results: int) -> list[dict[str, Any]]:
        try:
            from ddgs import DDGS

            results = []
            for item in DDGS().text(query, max_results=max_results):
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("href", ""),
                        "snippet": item.get("body", ""),
                        "source": "duckduckgo",
                        "score": 0.0,
                    }
                )
            return results
        except Exception as exc:
            logger.error("DuckDuckGo search failed: %s", exc)
            return []

    def _search_tavily(self, query: str, max_results: int) -> list[dict[str, Any]]:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.settings.tavily_api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": False,
            "search_depth": "advanced",
        }
        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logger.error("Tavily search failed: %s", exc)
            return []

        results = []
        for item in data.get("results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", "") or item.get("snippet", ""),
                    "source": "tavily",
                    "score": float(item.get("score") or 0),
                }
            )
        return results

    def _search_serpapi(self, query: str, max_results: int) -> list[dict[str, Any]]:
        params = {
            "engine": "google",
            "q": query,
            "api_key": self.settings.serpapi_api_key,
            "num": max_results,
        }
        try:
            with httpx.Client(timeout=30) as client:
                response = client.get("https://serpapi.com/search", params=params)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logger.error("SerpAPI search failed: %s", exc)
            return []

        results = []
        for item in data.get("organic_results", [])[:max_results]:
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source": "serpapi",
                    "score": 0.0,
                }
            )
        return results
