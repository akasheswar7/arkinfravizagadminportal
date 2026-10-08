from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class GalleryBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    image_url: str = Field(..., description="High-resolution image URL or video poster thumbnail")
    thumbnail_url: Optional[str] = None
    media_type: str = Field(default="photo", description="photo, site_visit, or video")
    video_url: Optional[str] = Field(default="", description="Video link or MP4 URL if media_type is video")
    category: str = Field(default="Events", description="Events, Site Visits, Milestones, Achievements, Videos, Other")
    description: Optional[str] = None
    is_published: bool = True

class GalleryCreate(GalleryBase):
    pass

class GalleryUpdate(BaseModel):
    title: Optional[str] = None
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    media_type: Optional[str] = None
    video_url: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    is_published: Optional[bool] = None

class GalleryResponse(GalleryBase):
    id: str
    created_at: datetime
    updated_at: datetime
