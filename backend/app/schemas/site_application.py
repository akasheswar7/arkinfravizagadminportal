from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class SiteApplicationBase(BaseModel):
    application_no: Optional[str] = None
    customer_id: Optional[str] = None
    customer_name: str = Field(..., min_length=2, max_length=150)
    father_or_spouse_name: Optional[str] = None
    phone: str = Field(..., min_length=7, max_length=25)
    alt_phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    aadhaar_or_id: Optional[str] = None
    photo_url: Optional[str] = None
    nominee_name: Optional[str] = None
    nominee_relation: Optional[str] = None
    nominee_phone: Optional[str] = None

    site_visit_date: Optional[str] = None
    site_visit_verified: bool = True
    site_visit_notes: Optional[str] = None

    venture_name: str = Field(..., min_length=2, max_length=150)
    plot_number: str = Field(..., min_length=1, max_length=50)
    plot_size: Optional[str] = None
    plot_facing: Optional[str] = None
    rate_per_sq_yd: Optional[str] = None
    total_site_value: Optional[str] = None

    supported_by: Optional[str] = None
    director_name: Optional[str] = None
    agent_name: Optional[str] = None

    advance_amount: str = Field(..., min_length=1)
    advance_amount_words: Optional[str] = None
    payment_mode: Optional[str] = "UPI / Online Transfer"
    transaction_id: Optional[str] = None
    payment_date: Optional[str] = None
    receipt_url: Optional[str] = None
    balance_amount: Optional[str] = None
    balance_due_date: Optional[str] = None

    verification_status: str = "Verified & Approved by ARK Infra"
    verified_by: str = "ARK Infra Management & MD/CEO Desk"
    remarks: Optional[str] = None

class SiteApplicationCreate(SiteApplicationBase):
    pass

class SiteApplicationUpdate(BaseModel):
    application_no: Optional[str] = None
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    father_or_spouse_name: Optional[str] = None
    phone: Optional[str] = None
    alt_phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    aadhaar_or_id: Optional[str] = None
    photo_url: Optional[str] = None
    nominee_name: Optional[str] = None
    nominee_relation: Optional[str] = None
    nominee_phone: Optional[str] = None

    site_visit_date: Optional[str] = None
    site_visit_verified: Optional[bool] = None
    site_visit_notes: Optional[str] = None

    venture_name: Optional[str] = None
    plot_number: Optional[str] = None
    plot_size: Optional[str] = None
    plot_facing: Optional[str] = None
    rate_per_sq_yd: Optional[str] = None
    total_site_value: Optional[str] = None

    supported_by: Optional[str] = None
    director_name: Optional[str] = None
    agent_name: Optional[str] = None

    advance_amount: Optional[str] = None
    advance_amount_words: Optional[str] = None
    payment_mode: Optional[str] = None
    transaction_id: Optional[str] = None
    payment_date: Optional[str] = None
    receipt_url: Optional[str] = None
    balance_amount: Optional[str] = None
    balance_due_date: Optional[str] = None

    verification_status: Optional[str] = None
    verified_by: Optional[str] = None
    remarks: Optional[str] = None

class SiteApplicationResponse(SiteApplicationBase):
    id: str
    created_at: datetime
    updated_at: datetime
