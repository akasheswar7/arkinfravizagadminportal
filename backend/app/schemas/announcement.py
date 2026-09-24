from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class AnnouncementBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    message: str = Field(..., min_length=2, max_length=1000)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    active: bool = True

class AnnouncementCreate(AnnouncementBase):
    pass

class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    active: Optional[bool] = None

class AnnouncementResponse(AnnouncementBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
