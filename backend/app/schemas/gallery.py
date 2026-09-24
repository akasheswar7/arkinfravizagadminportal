from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class GalleryBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    image_url: str = Field(..., description="High-resolution image URL")
    thumbnail_url: Optional[str] = None
    category: str = Field(default="Events", description="Events, Milestones, Achievements, Projects, Other, or site/event")
    description: Optional[str] = None
    is_published: bool = True

class GalleryCreate(GalleryBase):
    pass

class GalleryUpdate(BaseModel):
    title: Optional[str] = None
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    is_published: Optional[bool] = None

class GalleryResponse(GalleryBase):
    id: str
    created_at: datetime
    updated_at: datetime
