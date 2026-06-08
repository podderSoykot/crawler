from urllib.parse import urlparse

TRUSTED_DOMAINS = {
    "wikipedia.org": 100,
    "wikidata.org": 95,
    "gov.uk": 95,
    "gov.au": 95,
    "gov.in": 95,
    "gov": 90,
    "edu": 85,
    "ac.uk": 85,
    "who.int": 90,
    "un.org": 90,
    "europa.eu": 88,
    "nih.gov": 90,
    "nasa.gov": 88,
    "bbc.com": 75,
    "reuters.com": 78,
    "britannica.com": 82,
}

LOW_TRUST_HINTS = (
    "quora.com",
    "reddit.com",
    "pinterest.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
)


def _domain_score(url: str) -> float:
    try:
        host = urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return 0.0

    if any(hint in host for hint in LOW_TRUST_HINTS):
        return 10.0

    score = 40.0
    for pattern, bonus in TRUSTED_DOMAINS.items():
        if pattern in host:
            score = max(score, bonus)
    return score


def rank_sources(sources: list[dict]) -> list[dict]:
    """Sort search/crawl results by domain trust and optional API score."""
    ranked = []
    for item in sources:
        url = item.get("url") or item.get("link") or ""
        api_score = float(item.get("score") or 0)
        trust = _domain_score(url)
        combined = trust + min(api_score * 10, 20)
        ranked.append({**item, "trust_score": trust, "rank_score": combined})

    return sorted(ranked, key=lambda x: x["rank_score"], reverse=True)
