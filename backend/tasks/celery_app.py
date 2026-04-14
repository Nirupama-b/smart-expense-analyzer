import os
import sys

# Ensure the backend directory is on the Python path so that
# worker subprocesses can import top-level packages like 'services'.
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("smart_expense_analyzer")

celery_app.conf.update(
    broker_url=REDIS_URL,
    result_backend=REDIS_URL,
    # Reliability: acknowledge only after task completes successfully
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Retry defaults
    task_max_retries=3,
    task_default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    # Results
    result_expires=3600,
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Prefetch — one task at a time for fair distribution
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["tasks"], related_name="receipt_tasks")
