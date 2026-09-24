from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class DirectorBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    role: Optional[str] = "Director"
    profile_image: str = Field(..., description="URL of director profile photo")
    bio: str = Field(..., min_length=5)
    quote: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

class DirectorCreate(DirectorBase):
    pass

class DirectorUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    profile_image: Optional[str] = None
    bio: Optional[str] = None
    quote: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

class DirectorResponse(DirectorBase):
    id: str
    agents_count: Optional[int] = 0
    created_at: datetime
    updated_at: datetime
