from fastapi import APIRouter, UploadFile, File
import pandas as pd
import io
from data_cleaner import clean_question

router = APIRouter()

@router.post("/year-questions")
async def get_year_questions(file: UploadFile = File(...)):

    content = await file.read()
    filename = file.filename.lower()

    if filename.endswith(".csv"):
        df = pd.read_csv(io.StringIO(content.decode("utf-8")))
    else:
        df = pd.read_excel(io.BytesIO(content))

    results = []

    for q in df["question"].astype(str).tolist():

        res = clean_question(q)

        # only keep year-present questions
        if res and res["year"]:
            results.append(res)

    return {
        "status": "success",
        "input_rows": len(df),
        "output_rows": len(results),
        "data": results
    }