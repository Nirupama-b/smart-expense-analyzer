"""
Celery task pipeline for receipt processing.

Stages (chained):
  1. preprocess_image  — enhance image quality for OCR
  2. extract_text      — run OCR to pull raw text from the image
  3. categorize_expense — NLP categorization + amount/merchant extraction
"""

import os
import logging
from typing import Optional

# Force CPU-only for transformers/torch in forked Celery workers
# to prevent SIGABRT crashes from MPS on macOS
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

from celery import chain
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

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv(
            "SUPABASE_SERVICE_ROLE_KEY"
        )
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY (or "
                "SUPABASE_SERVICE_ROLE_KEY) must be set"
            )
        _supabase_client = create_client(url, key)
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
# Stage 1 — Image pre-processing
# ---------------------------------------------------------------------------
@celery_app.task(bind=True, max_retries=3, acks_late=True)
def preprocess_image(self, image_path: str, expense_id: str) -> dict:
    """Enhance the receipt image for better OCR accuracy."""
    try:
        _update_status(expense_id, "processing")

        from services.ocr_service import OCRService

        processed_path = OCRService.preprocess_image(image_path)
        return {
            "image_path": processed_path,
            "expense_id": expense_id,
        }
    except Exception as exc:
        logger.exception("preprocess_image failed for expense %s", expense_id)
        _update_status(expense_id, "failed")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


# ---------------------------------------------------------------------------
# Stage 2 — OCR text extraction
# ---------------------------------------------------------------------------
@celery_app.task(bind=True, max_retries=3, acks_late=True)
def extract_text(self, previous_result: dict) -> dict:
    """Run OCR on the preprocessed image and return extracted text."""
    image_path = previous_result["image_path"]
    expense_id = previous_result["expense_id"]
    try:
        _update_status(expense_id, "processing")

        from services.ocr_service import OCRService

        text = OCRService.extract_text(image_path)
        if not text or not text.strip():
            text = "Manual Entry Required"
        return {
            "image_path": image_path,
            "expense_id": expense_id,
            "extracted_text": text,
        }
    except Exception as exc:
        logger.exception("extract_text failed for expense %s", expense_id)
        _update_status(expense_id, "failed")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


# ---------------------------------------------------------------------------
# Stage 3 — NLP categorization + field extraction
# ---------------------------------------------------------------------------
@celery_app.task(bind=True, max_retries=3, acks_late=True)
def categorize_expense(self, previous_result: dict) -> dict:
    """Categorise expense text and extract amount / merchant."""
    expense_id = previous_result["expense_id"]
    extracted_text = previous_result["extracted_text"]
    try:
        _update_status(expense_id, "processing")

        from services.nlp_service import NLPCategorizationService
        from services.ocr_service import OCRService

        # Category
        category, confidence = NLPCategorizationService.categorize(extracted_text)

        # Amount & merchant
        amount = OCRService.extract_amount(extracted_text)
        merchant = OCRService.extract_merchant(extracted_text)

        # Decide final status
        final_status = "processed" if confidence >= 0.5 else "manual_review"

        # Look up category_id
        category_id = None
        try:
            cat_result = _get_supabase().table("categories").select("id").eq("name", category).execute()
            if cat_result.data:
                category_id = cat_result.data[0]["id"]
        except Exception:
            logger.warning("Could not look up category_id for %s", category)

        update_fields = {
            "raw_text": extracted_text,
        }
        if category_id is not None:
            update_fields["category_id"] = category_id
        if amount is not None:
            update_fields["amount"] = amount
        if merchant:
            update_fields["merchant"] = merchant

        _update_status(expense_id, final_status, extra=update_fields)

        return {
            "expense_id": expense_id,
            "category": category,
            "confidence": confidence,
            "amount": amount,
            "merchant": merchant,
            "status": final_status,
        }
    except Exception as exc:
        logger.exception("categorize_expense failed for expense %s", expense_id)
        _update_status(expense_id, "failed")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


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
        from services.ocr_service import OCRService
        from services.nlp_service import NLPCategorizationService

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

        _update_status(expense_id, final_status, extra=update_fields)

        return {
            "expense_id": expense_id,
            "category": category,
            "confidence": confidence,
            "amount": amount,
            "merchant": merchant,
            "status": final_status,
        }
    except Exception as exc:
        logger.exception("process_receipt failed for expense %s", expense_id)
        _update_status(expense_id, "failed")
        raise self.retry(exc=exc, countdown=5)
