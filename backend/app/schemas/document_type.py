from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

FieldType = Literal["string", "number", "date", "boolean"]


class DocumentTypeFieldIn(BaseModel):
    name: str
    type: FieldType
    description: str | None = None


class DocumentTypeFieldOut(DocumentTypeFieldIn):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class DocumentTypeCreate(BaseModel):
    name: str
    description: str | None = None
    fields: list[DocumentTypeFieldIn]

    @model_validator(mode="after")
    def check_unique_field_names(self) -> "DocumentTypeCreate":
        names = [field.name for field in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("Field names must be unique within a document type")
        return self


class DocumentTypeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    field_count: int
    created_by_email: str
    created_at: datetime


class DocumentTypeDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    fields: list[DocumentTypeFieldOut]
    created_by_email: str
    created_at: datetime
