from __future__ import annotations

import io
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader, PdfWriter


def _validate_page_range(page_start: int | None, page_end: int | None, total_pages: int) -> tuple[int, int]:
    start = page_start or 1
    end = page_end or total_pages
    if start < 1 or end < start or end > total_pages:
        raise HTTPException(status_code=400, detail="Enter a valid page range.")
    return start, end


def save_static_pdf_asset(
    upload: UploadFile,
    storage_root: str,
    page_start: int | None = None,
    page_end: int | None = None,
) -> tuple[str, str, str, int, int, int, int | None, int | None]:
    raw_bytes = upload.file.read()
    if not raw_bytes.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Upload a valid PDF file.")

    reader = PdfReader(io.BytesIO(raw_bytes))
    total_pages = len(reader.pages)
    start, end = _validate_page_range(page_start, page_end, total_pages)

    writer = PdfWriter()
    for page_index in range(start - 1, end):
        writer.add_page(reader.pages[page_index])

    out = io.BytesIO()
    writer.write(out)
    stored_bytes = out.getvalue()

    asset_id = uuid.uuid4()
    root = Path(storage_root)
    root.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{asset_id}.pdf"
    stored_path = root / stored_filename
    stored_path.write_bytes(stored_bytes)

    return (
        str(asset_id),
        upload.filename or "uploaded.pdf",
        stored_filename,
        str(stored_path),
        len(writer.pages),
        stored_path.stat().st_size,
        total_pages,
        start if start != 1 or page_start is not None else None,
        end if end != total_pages or page_end is not None else None,
    )
