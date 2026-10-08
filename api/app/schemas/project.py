from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class ProjectBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    tag: Optional[str] = Field(default="PLOTS", description="PLOTS, APARTMENTS, VILLA, PROPOSED, TLP APPROVED")
    status: Optional[str] = Field(default="Ongoing", description="Ongoing, Completed, Upcoming, Proposed")
    location: str = Field(..., description="e.g. Anakapalle, Tagarapuvalasa, Sabbavaram")
    price: Optional[str] = Field(default="", description="e.g. ₹12,500 / sq.yard or 35 Lakhs")
    description: Optional[str] = Field(default="", description="Short description of the venture/project")
    image_url: str = Field(..., description="Project card image URL")
    brochure_url: Optional[str] = None
    layout_features: Optional[List[str]] = Field(default_factory=list)
    project_highlights: Optional[List[str]] = Field(default_factory=list)
    location_highlights: Optional[List[str]] = Field(default_factory=list)
    is_published: bool = True

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    tag: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    price: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    brochure_url: Optional[str] = None
    layout_features: Optional[List[str]] = None
    project_highlights: Optional[List[str]] = None
    location_highlights: Optional[List[str]] = None
    is_published: Optional[bool] = None

class ProjectResponse(ProjectBase):
    id: str
    created_at: datetime
    updated_at: datetime
