from datetime import datetime
from typing import Literal
from uuid import UUID
import re

from pydantic import BaseModel, ConfigDict, model_validator, field_validator

FieldType = Literal["string", "number", "date", "boolean"]
OutputFormat = Literal["pdf", "xlsx"]

PARENT_SEGMENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(?:\[\])?$")
LEAF_SEGMENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")



class DocumentTypeFieldIn(BaseModel):
    name: str
    type: FieldType
    description: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name_path(cls, v: str) -> str:
        if not v:
            raise ValueError("Field name cannot be empty")
        segments = v.split(".")
        if len(segments) > 5:
            raise ValueError("Field path depth cannot exceed 5 levels")
        for i, segment in enumerate(segments):
            if not segment:
                raise ValueError("Field path segments cannot be empty")
            if i < len(segments) - 1:
                if not PARENT_SEGMENT_RE.match(segment):
                    raise ValueError(f"Invalid parent path segment: '{segment}'")
            else:
                if not LEAF_SEGMENT_RE.match(segment):
                    raise ValueError(f"Invalid leaf path segment: '{segment}'")
        return v


class DocumentTypeFieldOut(DocumentTypeFieldIn):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


MetadataType = Literal["text", "number", "date", "datetime", "boolean"]


class DocumentTypeMetadataIn(BaseModel):
    name: str
    type: MetadataType
    required: bool = True

    @field_validator("name")
    @classmethod
    def validate_metadata_name(cls, v: str) -> str:
        if not v:
            raise ValueError("Metadata name cannot be empty")
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v):
            raise ValueError(f"Invalid metadata name: '{v}'. Must be a valid identifier.")
        return v


class DocumentTypeMetadataOut(DocumentTypeMetadataIn):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class DocumentTypeCreate(BaseModel):
    name: str
    description: str | None = None
    fields: list[DocumentTypeFieldIn]
    metadata_definitions: list[DocumentTypeMetadataIn] = []
    allowed_output_formats: list[OutputFormat] = ["pdf"]

    @field_validator("allowed_output_formats")
    @classmethod
    def validate_allowed_output_formats(cls, values: list[OutputFormat]) -> list[OutputFormat]:
        if not values:
            raise ValueError("At least one output format must be allowed")
        if len(values) != len(set(values)):
            raise ValueError("Allowed output formats must be unique")
        return values

    @model_validator(mode="after")
    def validate_schema_structure(self) -> "DocumentTypeCreate":
        # 1. Check case-insensitive uniqueness of field names
        lower_names = [f.name.lower() for f in self.fields]
        if len(lower_names) != len(set(lower_names)):
            raise ValueError("Field names must be unique within a document type (case-insensitive)")

        # 2. Build the structural schema tree and detect conflicts
        root = {"type": "object", "children": {}}

        for field in self.fields:
            segments = field.name.split(".")
            current = root
            
            for idx, segment in enumerate(segments):
                is_last = (idx == len(segments) - 1)
                
                # Determine name and if it's a list
                if segment.endswith("[]"):
                    name = segment[:-2].lower()
                    is_list = True
                else:
                    name = segment.lower()
                    is_list = False
                
                # Check for structural conflict
                if is_last:
                    # Leaf segment
                    if name in current["children"]:
                        raise ValueError(f"Conflict: '{field.name}' collides with an existing field path or parent")
                    current["children"][name] = {
                        "type": "leaf",
                        "field_type": field.type
                    }
                else:
                    # Parent segment
                    if name in current["children"]:
                        existing = current["children"][name]
                        if is_list:
                            if existing["type"] != "list":
                                raise ValueError(f"Conflict: Path segment '{segment}' is declared as both a list and a non-list")
                            current = existing["element_node"]
                        else:
                            if existing["type"] != "object":
                                raise ValueError(f"Conflict: Path segment '{segment}' is declared as both an object and a non-object/leaf")
                            current = existing
                    else:
                        if is_list:
                            element_node = {"type": "object", "children": {}}
                            new_node = {
                                "type": "list",
                                "element_node": element_node
                            }
                            current["children"][name] = new_node
                            current = element_node
                        else:
                            new_node = {"type": "object", "children": {}}
                            current["children"][name] = new_node
                            current = new_node
        return self


class DocumentTypeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    allowed_output_formats: list[OutputFormat] = ["pdf"]
    field_count: int
    created_by_email: str
    created_at: datetime


class DocumentTypeDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    allowed_output_formats: list[OutputFormat] = ["pdf"]
    fields: list[DocumentTypeFieldOut]
    metadata_definitions: list[DocumentTypeMetadataOut] = []
    created_by_email: str
    created_at: datetime
