from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class CustomerBase(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=150)
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    photo_or_id: Optional[str] = None
    submission_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    site_visit_status: str = Field(
        default="Pending", 
        description="'Pending', 'Positive', 'Negative', 'Amount Paid', 'Fail', 'Site Visit Completed', 'Registration Completed'"
    )
    project_interested: Optional[str] = None
    plot_number: Optional[str] = None
    plot_size: Optional[str] = None
    advance_amount: Optional[str] = None
    receipt_url: Optional[str] = None
    supported_by: Optional[str] = None
    director_id: Optional[str] = None
    director_name: Optional[str] = None
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    notes: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    customer_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    photo_or_id: Optional[str] = None
    submission_date: Optional[str] = None
    site_visit_status: Optional[str] = None
    project_interested: Optional[str] = None
    plot_number: Optional[str] = None
    plot_size: Optional[str] = None
    advance_amount: Optional[str] = None
    receipt_url: Optional[str] = None
    supported_by: Optional[str] = None
    director_id: Optional[str] = None
    director_name: Optional[str] = None
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    notes: Optional[str] = None

class CustomerResponse(CustomerBase):
    id: str
    created_at: datetime
    updated_at: datetime
