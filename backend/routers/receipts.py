import logging
import os
import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from supabase import create_client

from config import get_settings
from middleware.auth import get_current_user
from models.schemas import ReceiptUploadResponse, TaskStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/receipts", tags=["receipts"])

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _get_admin_supabase():
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


# ---------------------------------------------------------------------------
# POST /api/receipts/upload
# ---------------------------------------------------------------------------
@router.post(
    "/upload",
    response_model=ReceiptUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_receipt(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    """Accept a receipt image, persist it, create a pending expense, and
    dispatch an async Celery task to process the receipt."""

    # --- validate content type ---
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed: jpeg, png, webp, heic",
        )

    # --- read and validate size ---
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    # --- save to disk ---
    settings = get_settings()
    ext = os.path.splitext(file.filename or "receipt.jpg")[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(contents)

    logger.info("Saved receipt image to %s (%d bytes)", filepath, len(contents))

    # --- create pending expense in Supabase ---
    supabase = _get_admin_supabase()
    expense_data = {
        "user_id": user_id,
        "amount": 0,
        "merchant": "Processing...",
        "date": date.today().isoformat(),
        "raw_text": None,
        "image_path": filepath,
        "status": "pending",
    }

    try:
        res = supabase.table("expenses").insert(expense_data).execute()
        expense_id = res.data[0]["id"]
    except Exception as exc:
        logger.error("Failed to create pending expense: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create expense record",
        )

    # --- dispatch Celery task ---
    try:
        from tasks.celery_app import celery_app

        task = celery_app.send_task(
            "tasks.process_receipt",
            args=[filepath, expense_id],
        )
        task_id = task.id
    except Exception as exc:
        logger.error("Failed to dispatch Celery task: %s", exc)
        # Update expense status to failed
        supabase.table("expenses").update({"status": "failed"}).eq(
            "id", expense_id
        ).execute()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue receipt processing task",
        )

    # --- store task reference in celery_tasks table ---
    try:
        supabase.table("celery_tasks").insert(
            {
                "task_id": task_id,
                "expense_id": expense_id,
                "status": "queued",
            }
        ).execute()
    except Exception as exc:
        logger.warning("Failed to record celery task row: %s", exc)

    logger.info(
        "Dispatched task %s for expense %s (user %s)", task_id, expense_id, user_id
    )

    return ReceiptUploadResponse(
        task_id=task_id,
        status="queued",
        message="Receipt uploaded and queued for processing",
    )


# ---------------------------------------------------------------------------
# GET /api/receipts/status/{task_id}
# ---------------------------------------------------------------------------
@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    user_id: str = Depends(get_current_user),
):
    """Check the processing status of a receipt upload task."""
    try:
        from tasks.celery_app import celery_app

        result = celery_app.AsyncResult(task_id)
    except Exception as exc:
        logger.error("Cannot resolve task %s: %s", task_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to check task status",
        )

    state = result.state  # PENDING | STARTED | SUCCESS | FAILURE | ...

    if state == "PENDING":
        return TaskStatusResponse(task_id=task_id, status="queued")
    elif state == "STARTED" or state == "RETRY":
        return TaskStatusResponse(task_id=task_id, status="processing")
    elif state == "SUCCESS":
        return TaskStatusResponse(
            task_id=task_id,
            status="completed",
            result=result.result,
        )
    elif state == "FAILURE":
        return TaskStatusResponse(
            task_id=task_id,
            status="failed",
            error=str(result.info) if result.info else "Unknown error",
        )
    else:
        return TaskStatusResponse(task_id=task_id, status=state.lower())
