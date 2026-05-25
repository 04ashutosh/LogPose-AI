from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class MessageCreate(BaseModel):
    role: str
    content: str
    agent_name: Optional[str] = None
    step_name: Optional[str] = None

class MessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    agent_name: Optional[str] = None
    step_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SessionCreate(BaseModel):
    title: str

class SessionResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True