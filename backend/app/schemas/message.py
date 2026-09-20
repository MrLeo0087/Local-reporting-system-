import uuid
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    body: str
    created_at: datetime
    sender_role: str  # "citizen" or "staff"
    sender_name: str
