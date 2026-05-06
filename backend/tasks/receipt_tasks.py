"""Celery task for receipt processing.

`process_receipt` is the only orchestrator task — it runs OCR, NLP
categorization, and field extraction inline (not as sub-tasks) so it
never deadlocks waiting on its own queue.
"""

import logging
import os
from typing import Optional

# Force CPU-only for transformers/torch in forked Celery workers
# to prevent SIGABRT crashes from MPS on macOS
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

from .celery_app import celery_app

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supabase helper (lazy-initialised)
# ---------------------------------------------------------------------------
_supabase_client = None


def _get_supabase():
    """Return a lazily-initialised Supabase admin client."""
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client

        from config import get_settings

        s = get_settings()
        _supabase_client = create_client(s.SUPABASE_URL, s.SUPABASE_SERVICE_KEY)
    return _supabase_client


def _update_status(expense_id: str, task_status: str, extra: Optional[dict] = None):
    """Update the task processing status (and optionally other fields) on an expense row."""
    data = {"status": task_status}
    if extra:
        data.update(extra)
    try:
        _get_supabase().table("expenses").update(data).eq("id", expense_id).execute()
    except Exception as exc:
        logger.error("Failed to update expense %s status: %s", expense_id, exc)


# ---------------------------------------------------------------------------
# Orchestrator — kick off the full pipeline
# ---------------------------------------------------------------------------
@celery_app.task(name="tasks.process_receipt", bind=True, max_retries=2)
def process_receipt(self, image_path: str, expense_id: str):
    """Run the full receipt processing pipeline sequentially.

    Calls each stage's implementation directly (not as async Celery tasks)
    to avoid deadlocks from blocking on sub-task results.
    """
    try:
        from services.nlp_service import NLPCategorizationService
        from services.ocr_service import OCRService

        # Mark as processing for the entire pipeline
        _update_status(expense_id, "processing")

        # Stage 1 — Image pre-processing
        processed_path = OCRService.preprocess_image(image_path)

        # Stage 2 — OCR text extraction
        text = OCRService.extract_text(processed_path)
        if not text or not text.strip():
            text = "Manual Entry Required"

        # Stage 3 — NLP categorization + field extraction
        category, confidence = NLPCategorizationService.categorize(text)
        amount = OCRService.extract_amount(text)
        merchant = OCRService.extract_merchant(text)
        receipt_date = OCRService.extract_date(text)  # ← FIXED: extract date from receipt

        final_status = "processed" if confidence >= 0.5 else "manual_review"

        # Look up category_id from categories table
        category_id = None
        try:
            cat_result = _get_supabase().table("categories").select("id").eq("name", category).execute()
            if cat_result.data:
                category_id = cat_result.data[0]["id"]
        except Exception:
            logger.warning("Could not look up category_id for %s", category)

        update_fields = {
            "raw_text": text,
        }
        if category_id is not None:
            update_fields["category_id"] = category_id
        if amount is not None:
            update_fields["amount"] = amount
        if merchant:
            update_fields["merchant"] = merchant
        if receipt_date:                              # ← FIXED: save date to DB
            update_fields["date"] = receipt_date

        _update_status(expense_id, final_status, extra=update_fields)

        return {
            "expense_id": expense_id,
            "category": category,
            "confidence": confidence,
            "amount": amount,
            "merchant": merchant,
            "receipt_date": receipt_date,
            "status": final_status,
        }
    except Exception as exc:
        logger.exception("process_receipt failed for expense %s", expense_id)
        _update_status(expense_id, "failed")
        raise self.retry(exc=exc, countdown=5)