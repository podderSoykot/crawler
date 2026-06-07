import json
from io import BytesIO
from typing import Any

import pandas as pd

QUESTION_ALIASES = ("question", "questions", "q", "query", "prompt", "title")
ANSWER_ALIASES = ("answer", "answers", "a", "response", "reply", "content")


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _pick_column(columns: list[str], aliases: tuple[str, ...]) -> str | None:
    for alias in aliases:
        if alias in columns:
            return alias
    for col in columns:
        if any(alias in col for alias in aliases):
            return col
    return None


def _records_from_dataframe(df: pd.DataFrame) -> list[dict[str, Any]]:
    df = _normalize_columns(df)
    question_col = _pick_column(list(df.columns), QUESTION_ALIASES)
    if not question_col:
        raise ValueError(
            "Could not find a question column. Expected one of: "
            + ", ".join(QUESTION_ALIASES)
        )

    answer_col = _pick_column(list(df.columns), ANSWER_ALIASES)
    records: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        question = str(row[question_col]).strip()
        if not question or question.lower() in ("nan", "none"):
            continue
        original_answer = None
        if answer_col and pd.notna(row.get(answer_col)):
            original_answer = str(row[answer_col]).strip()
        records.append({"question": question, "original_answer": original_answer})

    if not records:
        raise ValueError("No valid questions found in uploaded file.")
    return records


def parse_upload(filename: str, content: bytes) -> list[dict[str, Any]]:
    lower = filename.lower()

    if lower.endswith(".csv"):
        df = pd.read_csv(BytesIO(content))
        return _records_from_dataframe(df)

    if lower.endswith((".xlsx", ".xls")):
        df = pd.read_excel(BytesIO(content))
        return _records_from_dataframe(df)

    if lower.endswith(".json"):
        payload = json.loads(content.decode("utf-8"))
        if isinstance(payload, list):
            df = pd.DataFrame(payload)
            return _records_from_dataframe(df)
        if isinstance(payload, dict) and "items" in payload:
            df = pd.DataFrame(payload["items"])
            return _records_from_dataframe(df)
        raise ValueError("JSON must be a list of objects or {\"items\": [...]}.")

    raise ValueError("Unsupported file type. Use CSV, Excel (.xlsx), or JSON.")
