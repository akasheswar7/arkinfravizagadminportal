from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends
from app.core.database import get_collection
from app.core.security import verify_password, create_access_token, get_current_admin
from app.schemas.admin import AdminLoginRequest, AdminTokenResponse, AdminProfile

router = APIRouter(prefix="/admin", tags=["Authentication"])

@router.post("/login", response_model=AdminTokenResponse)
async def login(credentials: AdminLoginRequest):
    """Authenticates the admin and returns a signed JWT."""
    admins_col = get_collection("admins")
    admin = await admins_col.find_one({
        "$or": [
            {"email": credentials.username_or_email.lower().strip()},
            {"username": credentials.username_or_email.strip()}
        ]
    })

    if not admin or not verify_password(credentials.password, admin.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password."
        )

    # Update last login timestamp
    await admins_col.update_one(
        {"_id": admin["_id"]},
        {"$set": {"last_login": datetime.now(timezone.utc)}}
    )

    token = create_access_token({"sub": admin["email"], "role": admin.get("role", "admin")})
    return AdminTokenResponse(
        access_token=token,
        token_type="bearer",
        admin_id=str(admin["_id"]),
        email=admin["email"],
        full_name=admin.get("full_name", "ARK Infra Admin")
    )

@router.get("/me", response_model=AdminProfile)
async def get_my_profile(current_admin: dict = Depends(get_current_admin)):
    """Returns the authenticated admin's profile."""
    return AdminProfile(
        id=current_admin["id"],
        email=current_admin["email"],
        full_name=current_admin.get("full_name", "Admin"),
        role=current_admin.get("role", "admin")
    )

@router.post("/logout")
async def logout(current_admin: dict = Depends(get_current_admin)):
    """Logs out the admin (client also discards the token)."""
    return {"message": "Logged out successfully."}
