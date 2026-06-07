from fastapi import APIRouter, UploadFile, File
import pandas as pd
import io
from data_cleaner import clean_question

router = APIRouter()


@router.post("/process-file")
async def process_file(file: UploadFile = File(...)):

    content = await file.read()
    filename = file.filename.lower()

    if filename.endswith(".csv"):
        df = pd.read_csv(io.StringIO(content.decode("utf-8")))
    else:
        df = pd.read_excel(io.BytesIO(content))

    results = []

    for q in df["question"].astype(str).tolist():
        res = clean_question(q)
        if res:
            results.append(res)

    return {
        "input_rows": len(df),
        "output_rows": len(results),
        "data": results
    }


@router.post("/process-json")
async def process_json(payload: dict):

    results = []

    for item in payload.get("data", []):
        res = clean_question(item.get("question", ""))
        if res:
            results.append(res)

    return {
        "input_rows": len(payload.get("data", [])),
        "output_rows": len(results),
        "data": results
    }