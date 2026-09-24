from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class CustomerBase(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=150)
    phone: Optional[str] = None
    email: Optional[str] = None
    photo_or_id: Optional[str] = None
    submission_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    site_visit_status: str = Field(default="Pending", description="'Pending', 'Site Visit Completed', or 'Registration Completed'")
    project_interested: Optional[str] = None
    notes: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    customer_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    photo_or_id: Optional[str] = None
    submission_date: Optional[str] = None
    site_visit_status: Optional[str] = None
    project_interested: Optional[str] = None
    notes: Optional[str] = None

class CustomerResponse(CustomerBase):
    id: str
    created_at: datetime
    updated_at: datetime
