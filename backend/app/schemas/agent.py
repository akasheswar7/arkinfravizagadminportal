from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class AgentBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    profile_image: str = Field(..., description="URL of agent profile photo")
    phone: str = Field(..., min_length=6, max_length=30)
    director_id: str = Field(..., description="ID of the reporting Director")
    team_head_name: Optional[str] = None
    designation: Optional[str] = "Real Estate Agent"
    email: Optional[str] = None

class AgentCreate(AgentBase):
    pass

class AgentUpdate(BaseModel):
    full_name: Optional[str] = None
    profile_image: Optional[str] = None
    phone: Optional[str] = None
    director_id: Optional[str] = None
    team_head_name: Optional[str] = None
    designation: Optional[str] = None
    email: Optional[str] = None

class AgentResponse(AgentBase):
    id: str
    director_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
