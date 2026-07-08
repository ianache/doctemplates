from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class DocumentIssuanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    design_version_id: UUID
    file_path: str
    user_id: UUID
    input_data: dict
    created_at: datetime
