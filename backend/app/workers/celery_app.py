from celery import Celery
from app.config import settings

celery_app = Celery(
    "docmanagement",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=600,
    task_soft_time_limit=540,
    task_always_eager=settings.celery_task_always_eager,
    imports=["app.workers.document_generation"],
)
