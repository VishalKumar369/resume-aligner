from datetime import datetime
from typing import Optional, Any, Dict
from uuid import UUID
from pydantic import BaseModel, ConfigDict, HttpUrl

class JDBase(BaseModel):
    title: str
    company_name: Optional[str] = None
    url: Optional[HttpUrl] = None

class JDCreate(JDBase):
    raw_text: str

class JDUploadSchema(BaseModel):
    title: str
    company_name: Optional[str] = None
    url: Optional[str] = None
    raw_text: Optional[str] = None

class JDOut(JDBase):
    id: UUID
    owner_id: UUID
    created_at: datetime
    structured_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
