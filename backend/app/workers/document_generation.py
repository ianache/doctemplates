import logging
import uuid
from datetime import datetime
from sqlalchemy.orm import joinedload, selectinload

from app.workers.celery_app import celery_app
from app.db import SessionLocal
from app.models.document_issuance import DocumentIssuance
from app.models.document_tracelog import DocumentTracelog
from app.models.document_design import DocumentDesign
from app.services.pdf_generator import generate_composed_pdf
from app.dependencies import get_storage_provider

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.document_generation.generate_document_pdf")
def generate_document_pdf(issuance_id: str) -> None:
    """Task to generate a composed PDF document asynchronously."""
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
                selectinload(DocumentDesign.pages),
            )
            .filter(DocumentDesign.id == issuance.design_version_id)
            .first()
        )

        if not design:
            raise ValueError(f"DocumentDesign {issuance.design_version_id} not found.")

        # 2. Generate PDF bytes
        storage_provider = get_storage_provider()
        pdf_bytes = generate_composed_pdf(
            design,
            issuance.input_data,
            db,
            storage_provider,
            mock_fallback=False
        )

        # 3. Save to storage
        storage_key = storage_provider.save(
            f"{issuance.id}.pdf",
            pdf_bytes,
            category="issuances"
        )

        # 4. Update status to success
        issuance.storage_key = storage_key
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
        logger.info(f"Successfully generated PDF for DocumentIssuance {issuance_id}")

    except Exception as e:
        db.rollback()
        logger.exception(f"Error generating PDF for DocumentIssuance {issuance_id}")
        
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
