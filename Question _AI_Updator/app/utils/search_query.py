import re


FILLER_PREFIXES = (
    "who is the",
    "who is",
    "what is the",
    "what is",
    "where is the",
    "where is",
    "when did",
    "how many",
    "tell me",
    "can you tell me",
)

TIME_SENSITIVE_KEYWORDS = (
    "current",
    "currently",
    "today",
    "now",
    "latest",
    "recent",
    "richest",
    "wealthiest",
    "billionaire",
    "president",
    "prime minister",
    "ceo",
)


def build_search_query(question: str, year: int = 2026) -> str:
    q = question.strip().rstrip("?").lower()
    q = re.sub(r"\s+", " ", q)

    for prefix in FILLER_PREFIXES:
        if q.startswith(prefix):
            q = q[len(prefix) :].strip()
            break

    q = re.sub(r"\b(the|a|an|most)\b", " ", q)
    q = re.sub(r"\s+", " ", q).strip()

    if any(keyword in question.lower() for keyword in TIME_SENSITIVE_KEYWORDS):
        q = f"{q} {year}"

    return q
