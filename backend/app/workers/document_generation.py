import logging
import uuid
from datetime import datetime
from sqlalchemy.orm import joinedload, selectinload

from app.workers.celery_app import celery_app
from app.db import SessionLocal
from app.models.document_issuance import DocumentIssuance
from app.models.document_tracelog import DocumentTracelog
from app.models.document_design import DocumentDesign
from app.services.document_generation import generate_document_file
from app.dependencies import get_storage_provider

logger = logging.getLogger(__name__)


def _generate_document_impl(issuance_id: str) -> None:
    db = SessionLocal()
    try:
        issuance_uuid = issuance_id if isinstance(issuance_id, uuid.UUID) else uuid.UUID(issuance_id)
        # Lock issuance row for update to prevent concurrent task runs from racing
        issuance = (
            db.query(DocumentIssuance)
            .filter(DocumentIssuance.id == issuance_uuid)
            .with_for_update()
            .first()
        )

        if not issuance:
            logger.error(f"DocumentIssuance {issuance_id} not found.")
            return

        if issuance.status != "queued":
            logger.info(f"DocumentIssuance {issuance_id} has status '{issuance.status}'. Skipping generation.")
            return

        # 1. Update status to processing
        issuance.status = "processing"
        issuance.started_at = datetime.utcnow()
        db.commit()

        # Re-fetch for generation logic to ensure we are operating on clean DB state
        design = (
            db.query(DocumentDesign)
            .options(
                joinedload(DocumentDesign.document_type),
                joinedload(DocumentDesign.created_by),
                joinedload(DocumentDesign.xlsx_template),
                selectinload(DocumentDesign.pages),
            )
            .filter(DocumentDesign.id == issuance.design_version_id)
            .first()
        )

        if not design:
            raise ValueError(f"DocumentDesign {issuance.design_version_id} not found.")

        # 2. Generate document bytes
        storage_provider = get_storage_provider()
        issuance.design_version = design
        generated = generate_document_file(issuance, db, storage_provider)

        # 3. Save to storage
        storage_key = storage_provider.save(
            f"{issuance.id}.{generated.extension}",
            generated.content,
            category="issuances"
        )

        # 4. Update status to success
        issuance.storage_key = storage_key
        issuance.output_format = design.output_format
        issuance.mime_type = generated.mime_type
        issuance.filename = generated.filename
        issuance.status = "success"
        issuance.completed_at = datetime.utcnow()

        # 5. Create tracelog
        tracelog = DocumentTracelog(
            issuance_id=issuance.id,
            user_id=issuance.user_id,
            event_type="generation",
            metadata_={
                "source": "Celery Worker",
                "design_id": str(design.id),
            },
        )
        db.add(tracelog)
        db.commit()
        logger.info(f"Successfully generated document for DocumentIssuance {issuance_id}")

    except Exception as e:
        db.rollback()
        logger.exception(f"Error generating document for DocumentIssuance {issuance_id}")
        
        # Open a new transaction to record the failure status securely
        fail_db = SessionLocal()
        try:
            issuance_uuid = issuance_id if isinstance(issuance_id, uuid.UUID) else uuid.UUID(issuance_id)
            issuance = fail_db.query(DocumentIssuance).filter(DocumentIssuance.id == issuance_uuid).first()
            if issuance:
                issuance.status = "failure"
                # Truncate error message to avoid DB constraints or excessive sizes
                issuance.error_message = str(e)[:1000]
                issuance.completed_at = datetime.utcnow()
                fail_db.commit()
        except Exception as fail_err:
            logger.exception(f"Failed to record failure status for {issuance_id}: {fail_err}")
        finally:
            fail_db.close()
        
        raise e
    finally:
        db.close()


@celery_app.task(name="app.workers.document_generation.generate_document")
def generate_document(issuance_id: str) -> None:
    """Task to generate a document file asynchronously."""
    return _generate_document_impl(issuance_id)


@celery_app.task(name="app.workers.document_generation.generate_document_pdf")
def generate_document_pdf(issuance_id: str) -> None:
    """Backward-compatible task name for already queued PDF generation jobs."""
    return _generate_document_impl(issuance_id)
