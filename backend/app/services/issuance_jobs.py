def enqueue_document_generation(issuance_id: str) -> str:
    """Enqueues document generation via a Celery worker task.

    Lazily imports the task to allow app startup and testing before the
    worker module is fully defined.
    """
    from app.workers.document_generation import generate_document_pdf
    task = generate_document_pdf.delay(issuance_id)
    return str(task.id)
