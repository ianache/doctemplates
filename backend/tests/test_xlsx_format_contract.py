from uuid import UUID

import pytest
from pydantic import ValidationError

from app.models.document_design import DESIGN_OUTPUT_FORMATS
from app.models.document_type import DEFAULT_OUTPUT_FORMATS
from app.schemas.document_design import DocumentDesignCreate
from app.schemas.document_type import DocumentTypeCreate


def test_document_type_defaults_to_pdf_format():
    payload = DocumentTypeCreate(
        name="Contract",
        description=None,
        fields=[],
        metadata_definitions=[],
    )

    assert payload.allowed_output_formats == ["pdf"]
    assert DEFAULT_OUTPUT_FORMATS == ["pdf"]


def test_document_design_accepts_xlsx_output_format():
    payload = DocumentDesignCreate(
        document_type_id=UUID("00000000-0000-0000-0000-000000000001"),
        name="Workbook design",
        description=None,
        output_format="xlsx",
        xlsx_template_id=UUID("00000000-0000-0000-0000-000000000002"),
        mock_data=None,
    )

    assert payload.output_format == "xlsx"
    assert payload.xlsx_template_id is not None
    assert DESIGN_OUTPUT_FORMATS == ("pdf", "xlsx")


@pytest.mark.parametrize("formats", [[], ["pdf", "pdf"]])
def test_document_type_rejects_empty_or_duplicate_output_formats(formats):
    with pytest.raises(ValidationError):
        DocumentTypeCreate(
            name="Contract",
            fields=[],
            allowed_output_formats=formats,
        )


def test_document_design_rejects_invalid_output_format():
    with pytest.raises(ValidationError):
        DocumentDesignCreate(
            document_type_id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Invalid design",
            output_format="docx",
        )
