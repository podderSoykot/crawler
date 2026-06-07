from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.upload_service import UploadService
from app.workers.tasks import process_batch_task

router = APIRouter(prefix="/upload", tags=["upload"])
upload_service = UploadService()


@router.post("")
async def upload_dataset(
    file: UploadFile = File(...),
    auto_process: bool = False,
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        result = upload_service.create_batch_from_upload(db, file.filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if auto_process:
        task = process_batch_task.delay(result["batch_id"])
        result["task_id"] = task.id
        result["processing"] = "queued"

    return result
