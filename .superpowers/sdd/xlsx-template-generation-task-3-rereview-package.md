# Task 3 Re-Review Package
?? .superpowers/sdd/xlsx-template-generation-task-3-report.md
?? backend/app/services/xlsx_images.py
?? backend/app/services/xlsx_renderer.py
?? backend/tests/test_xlsx_renderer.py

## File: backend/app/services/xlsx_renderer.py
```
import copy
import json
from io import BytesIO
from typing import Any

from jinja2.sandbox import SandboxedEnvironment
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.utils.cell import range_boundaries
from openpyxl.worksheet.worksheet import Worksheet

from app.services.xlsx_images import normalize_image_value


_JINJA_ENV = SandboxedEnvironment(autoescape=False)
_REPEAT_DEFINED_NAME = "_docman_repeats"


def render_xlsx_template(
    workbook_bytes: bytes,
    payload: dict,
    image_values: dict | None = None,
) -> bytes:
    workbook = load_workbook(BytesIO(workbook_bytes), data_only=False)
    repeat_rows = _render_repeat_rows(workbook, payload)

    for worksheet in workbook.worksheets:
        skipped_rows = repeat_rows.get(worksheet.title, set())
        for row in worksheet.iter_rows():
            for cell in row:
                if cell.row in skipped_rows:
                    continue
                _render_cell(cell, payload)

    _insert_images(workbook, image_values or {})

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def preview_xlsx_template(workbook_bytes: bytes, payload: dict) -> dict:
    rendered_bytes = render_xlsx_template(workbook_bytes, payload)
    workbook = load_workbook(BytesIO(rendered_bytes), data_only=False)
    sheets: list[dict] = []

    for worksheet in workbook.worksheets:
        cells = []
        for row in worksheet.iter_rows():
            for cell in row:
                if cell.value is not None:
                    cells.append({"address": cell.coordinate, "value": cell.value, "style": {}})
        sheets.append(
            {
                "name": worksheet.title,
                "max_row": worksheet.max_row,
                "max_column": worksheet.max_column,
                "merged_ranges": [str(cell_range) for cell_range in worksheet.merged_cells.ranges],
                "cells": cells,
            }
        )

    return {"sheets": sheets, "warnings": []}


def _render_repeat_rows(workbook, payload: dict) -> dict[str, set[int]]:
    rendered_rows: dict[str, set[int]] = {}
    offset_by_sheet: dict[str, int] = {}

    for spec in _load_repeat_specs(workbook):
        sheet_name = spec["sheet"]
        worksheet = workbook[sheet_name]
        row_index = int(spec["row"]) + offset_by_sheet.get(sheet_name, 0)
        items = _resolve_path(payload, spec["list"])
        if items is None:
            items = []
        if not isinstance(items, list):
            raise ValueError("repeat_list_must_be_array")

        _reject_merged_repeat_row(worksheet, row_index)
        rendered = _render_repeat_row(worksheet, row_index, payload, items)
        rendered_rows.setdefault(sheet_name, set()).update(rendered)
        offset_by_sheet[sheet_name] = offset_by_sheet.get(sheet_name, 0) + len(items) - 1

    return rendered_rows


def _load_repeat_specs(workbook) -> list[dict]:
    defined_name = workbook.defined_names.get(_REPEAT_DEFINED_NAME)
    if defined_name is None:
        return []

    specs: list[dict] = []
    for sheet_name, coordinate in defined_name.destinations:
        worksheet = workbook[sheet_name]
        raw_value = worksheet[coordinate].value
        if raw_value in (None, ""):
            continue
        parsed = json.loads(raw_value)
        if not isinstance(parsed, list):
            raise ValueError("invalid_repeat_metadata")
        for item in parsed:
            if not isinstance(item, dict) or not {"sheet", "row", "list"} <= item.keys():
                raise ValueError("invalid_repeat_metadata")
            specs.append(item)

    return sorted(specs, key=lambda spec: (spec["sheet"], int(spec["row"])))


def _render_repeat_row(worksheet: Worksheet, row_index: int, payload: dict, items: list[dict]) -> set[int]:
    if not items:
        worksheet.delete_rows(row_index, 1)
        return set()

    template_cells = [_snapshot_cell(cell) for cell in worksheet[row_index]]
    template_height = worksheet.row_dimensions[row_index].height
    if len(items) > 1:
        worksheet.insert_rows(row_index + 1, len(items) - 1)

    rendered_rows: set[int] = set()
    for item_index, item in enumerate(items):
        target_row = row_index + item_index
        rendered_rows.add(target_row)
        if template_height is not None:
            worksheet.row_dimensions[target_row].height = template_height
        for template_cell in template_cells:
            target_cell = worksheet.cell(row=target_row, column=template_cell["column"])
            _apply_cell_snapshot(template_cell, target_cell)
            context = {**payload, "item": item}
            _render_cell(target_cell, context)

    return rendered_rows


def _snapshot_cell(cell) -> dict:
    return {
        "column": cell.column,
        "value": cell.value,
        "has_style": cell.has_style,
        "style": copy.copy(cell._style),
        "number_format": cell.number_format,
        "font": copy.copy(cell.font),
        "fill": copy.copy(cell.fill),
        "border": copy.copy(cell.border),
        "alignment": copy.copy(cell.alignment),
        "protection": copy.copy(cell.protection),
    }


def _apply_cell_snapshot(snapshot: dict, target) -> None:
    target.value = snapshot["value"]
    if snapshot["has_style"]:
        target._style = copy.copy(snapshot["style"])
    target.number_format = snapshot["number_format"]
    target.font = copy.copy(snapshot["font"])
    target.fill = copy.copy(snapshot["fill"])
    target.border = copy.copy(snapshot["border"])
    target.alignment = copy.copy(snapshot["alignment"])
    target.protection = copy.copy(snapshot["protection"])


def _render_cell(cell, context: dict) -> None:
    if isinstance(cell.value, str) and "{{" in cell.value:
        cell.value = _escape_formula_text(_JINJA_ENV.from_string(cell.value).render(context))


def _escape_formula_text(value: str) -> str:
    if value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


def _insert_images(workbook, image_values: dict) -> None:
    for anchor, raw_value in image_values.items():
        if "!" not in anchor:
            raise ValueError("invalid_image_anchor")
        sheet_name, cell_coordinate = anchor.split("!", 1)
        if sheet_name not in workbook.sheetnames:
            raise ValueError("invalid_image_anchor")
        normalized = normalize_image_value(raw_value)
        image = OpenpyxlImage(BytesIO(normalized.content))
        image.anchor = cell_coordinate
        workbook[sheet_name].add_image(image)


def _reject_merged_repeat_row(worksheet: Worksheet, row_index: int) -> None:
    for merged_range in worksheet.merged_cells.ranges:
        min_col, min_row, max_col, max_row = range_boundaries(str(merged_range))
        del min_col, max_col
        if min_row <= row_index <= max_row:
            raise ValueError("unsupported_merge_in_repeat_range")


def _resolve_path(payload: dict, path: str) -> Any:
    current: Any = payload
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current

```

## File: backend/app/services/xlsx_images.py
```
import base64
import binascii
from dataclasses import dataclass
from io import BytesIO

from PIL import Image


@dataclass(frozen=True)
class NormalizedImage:
    mime_type: str
    content: bytes
    width: int
    height: int


def normalize_image_value(value: object) -> NormalizedImage:
    if not isinstance(value, str) or not value.startswith("data:image/"):
        raise ValueError("invalid_image_payload")

    try:
        header, encoded = value.split(",", 1)
    except ValueError as exc:
        raise ValueError("invalid_image_payload") from exc

    mime_type = header.removeprefix("data:").split(";", 1)[0]
    if mime_type not in {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"}:
        raise ValueError("unsupported_image_type")

    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("invalid_image_payload") from exc

    try:
        with Image.open(BytesIO(content)) as image:
            width, height = image.size
    except Exception as exc:
        raise ValueError("invalid_image_payload") from exc

    return NormalizedImage(mime_type=mime_type, content=content, width=width, height=height)

```

## File: backend/tests/test_xlsx_renderer.py
```
from io import BytesIO

import pytest
from openpyxl import Workbook, load_workbook
from openpyxl.workbook.defined_name import DefinedName

from app.services.xlsx_images import normalize_image_value
from app.services.xlsx_renderer import render_xlsx_template


def _summary_workbook_bytes() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Summary"
    worksheet["A1"] = "Customer"
    worksheet["B1"] = "{{cliente.nombre}}"
    worksheet["C1"] = "=SUM(1,2)"
    worksheet.column_dimensions["B"].width = 30
    worksheet.print_area = "A1:C10"
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _repeat_workbook_bytes(repeat_json: str = '[{"sheet":"Items","row":2,"list":"items"}]') -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Items"
    worksheet["A1"] = "Name"
    worksheet["B1"] = "Qty"
    worksheet["A2"] = "{{item.name}}"
    worksheet["B2"] = "{{item.qty}}"
    worksheet["Z1"] = repeat_json
    worksheet.column_dimensions["Z"].hidden = True
    workbook.defined_names.add(DefinedName("_docman_repeats", attr_text="'Items'!$Z$1"))
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_render_replaces_cell_token_and_preserves_workbook_structure() -> None:
    output = render_xlsx_template(_summary_workbook_bytes(), {"cliente": {"nombre": "ACME"}})
    workbook = load_workbook(BytesIO(output), data_only=False)
    worksheet = workbook["Summary"]

    assert worksheet["B1"].value == "ACME"
    assert str(worksheet.print_area) == "'Summary'!$A$1:$C$10"
    assert worksheet.column_dimensions["B"].width == 30
    assert worksheet["C1"].value == "=SUM(1,2)"


def test_render_escapes_payload_formula_values() -> None:
    output = render_xlsx_template(_summary_workbook_bytes(), {"cliente": {"nombre": "=HYPERLINK(\"x\")"}})
    workbook = load_workbook(BytesIO(output), data_only=False)

    assert workbook["Summary"]["B1"].value == "'=HYPERLINK(\"x\")"


def test_render_repeats_explicit_row_for_list_items() -> None:
    output = render_xlsx_template(
        _repeat_workbook_bytes(),
        {"items": [{"name": "A", "qty": 1}, {"name": "B", "qty": 2}]},
    )
    rendered = load_workbook(BytesIO(output))["Items"]

    assert rendered["A2"].value == "A"
    assert rendered["B2"].value == "1"
    assert rendered["A3"].value == "B"
    assert rendered["B3"].value == "2"


def test_empty_repeat_row_updates_later_repeat_offsets() -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Items"
    worksheet["A2"] = "{{item.name}}"
    worksheet["A3"] = "{{item.name}}"
    worksheet["Z1"] = (
        '[{"sheet":"Items","row":2,"list":"empty_items"},'
        '{"sheet":"Items","row":3,"list":"items"}]'
    )
    worksheet.column_dimensions["Z"].hidden = True
    workbook.defined_names.add(DefinedName("_docman_repeats", attr_text="'Items'!$Z$1"))
    buffer = BytesIO()
    workbook.save(buffer)

    output = render_xlsx_template(buffer.getvalue(), {"empty_items": [], "items": [{"name": "A"}]})
    rendered = load_workbook(BytesIO(output))["Items"]

    assert rendered["A2"].value == "A"
    assert rendered["A3"].value is None


def test_render_rejects_merged_cells_intersecting_repeat_row() -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Items"
    worksheet["A2"] = "{{item.name}}"
    worksheet.merge_cells("A2:B2")
    worksheet["Z1"] = '[{"sheet":"Items","row":2,"list":"items"}]'
    workbook.defined_names.add(DefinedName("_docman_repeats", attr_text="'Items'!$Z$1"))
    buffer = BytesIO()
    workbook.save(buffer)

    with pytest.raises(ValueError, match="unsupported_merge_in_repeat_range"):
        render_xlsx_template(buffer.getvalue(), {"items": [{"name": "A"}]})


def test_normalize_png_data_url() -> None:
    data_url = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )

    image = normalize_image_value(data_url)

    assert image.mime_type == "image/png"
    assert image.width >= 1
    assert image.height >= 1


def test_render_inserts_explicitly_anchored_image() -> None:
    data_url = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )

    output = render_xlsx_template(_summary_workbook_bytes(), {}, {"Summary!D4": data_url})
    workbook = load_workbook(BytesIO(output))

    assert len(workbook["Summary"]._images) == 1


def test_normalize_rejects_invalid_base64_data_url() -> None:
    with pytest.raises(ValueError, match="invalid_image_payload"):
        normalize_image_value("data:image/png;base64,not-valid-base64")

```

## File: .superpowers/sdd/xlsx-template-generation-task-3-report.md
```
# XLSX Template Generation Task 3 Report

## Status

Implemented Task 3 renderer and image normalization work:

- Added sandboxed Jinja cell rendering for XLSX workbooks.
- Preserved workbook structure for non-token cells, including formulas, print area, and column widths.
- Added explicit `_docman_repeats` defined-name convention for repeated rows.
- Rejected merged cells intersecting repeated template rows with `unsupported_merge_in_repeat_range`.
- Added Pillow-backed data URL image normalization.
- Added a service-level preview helper for rendered workbook cells; no preview API was implemented.

## Changed Files

- `backend/app/services/xlsx_renderer.py`
- `backend/app/services/xlsx_images.py`
- `backend/tests/test_xlsx_renderer.py`
- `.superpowers/sdd/xlsx-template-generation-task-3-report.md`

## Test Summary

TDD red checks:

- `rtk pytest backend/tests/test_xlsx_renderer.py::test_render_replaces_cell_token_and_preserves_workbook_structure -q`
  - Failed before collection output was visible through `rtk`.
- Raw rerun with required settings:
  - `pytest backend/tests/test_xlsx_renderer.py::test_render_replaces_cell_token_and_preserves_workbook_structure -q`
  - Blocked before test collection by unrelated app import: `ModuleNotFoundError: No module named 'xhtml2pdf'`.

Verification completed:

- Direct service-level checks with `PYTHONPATH=backend` passed for:
  - token replacement and workbook structure preservation,
  - repeated row expansion,
  - merged repeat row rejection,
  - PNG data URL normalization.
- `rtk python -m compileall backend/app/services/xlsx_renderer.py backend/app/services/xlsx_images.py backend/tests/test_xlsx_renderer.py`
  - Passed.

## Concerns

- Focused pytest is currently blocked by `backend/tests/conftest.py` importing `app.main`, which imports `app.services.pdf_generator`, which requires missing dependency `xhtml2pdf`.
- The repository has many pre-existing dirty/untracked/deleted files outside the Task 3 write set. They were not modified or reverted.
- `image_values` is accepted by `render_xlsx_template` for the planned interface, but workbook image insertion metadata is not specified in Task 3 and was not implemented beyond normalization.
 
---

## Review Fix Report

Fixed Task 3 review findings:

- Escaped rendered strings that start with formula markers (`=`, `+`, `-`, `@`) before assigning to XLSX cells.
- Applied negative row offsets for empty repeated rows and sorted repeat specs top-to-bottom by sheet/row.
- Implemented minimal explicit image insertion via `image_values` anchors like `Summary!D4`.
- Caught `binascii.Error` for malformed base64 image payloads.
- Added regression tests for formula escaping, empty-repeat offsets, explicit image insertion, and malformed base64.

Verification:

- `rtk proxy python -m compileall -q backend/app/services/xlsx_renderer.py backend/app/services/xlsx_images.py backend/tests/test_xlsx_renderer.py`: passed.
- `rtk pytest backend/tests/test_xlsx_renderer.py -q`: failed with no useful detail after filtering.
- `rtk proxy powershell -NoProfile -Command '& { Set-Location backend; uv run pytest tests/test_xlsx_renderer.py -q }'`: blocked by `failed to open file C:\Users\ilver\AppData\Local\uv\cache\sdists-v9\.git: Access is denied. (os error 5)`.

```
