from typing import Optional
from pydantic import BaseModel, EmailStr

class AdminLoginRequest(BaseModel):
    username_or_email: str
    password: str

class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin_id: str
    email: str
    full_name: str

class AdminProfile(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str = "admin"
