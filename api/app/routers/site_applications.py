import re
from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends, Query, Response
from app.core.database import get_collection
from app.core.security import get_current_admin
from app.schemas.site_application import (
    SiteApplicationCreate,
    SiteApplicationUpdate,
    SiteApplicationResponse
)
from app.services.pdf_service import generate_site_application_pdf

router = APIRouter(prefix="/admin/site-applications", tags=["Site Bookings & Customer Applications"])

def _format_app(doc: dict) -> dict:
    created = doc.get("created_at") or datetime.now(timezone.utc)
    updated = doc.get("updated_at") or datetime.now(timezone.utc)
    created_str = created.strftime("%Y-%m-%d") if hasattr(created, "strftime") else str(created)[:10]

    return {
        "id": str(doc["_id"]),
        "application_no": doc.get("application_no") or f"ARK-APP-{str(doc['_id'])[-6:].upper()}",
        "customer_id": doc.get("customer_id"),
        "customer_name": doc.get("customer_name", ""),
        "father_or_spouse_name": doc.get("father_or_spouse_name"),
        "phone": doc.get("phone", ""),
        "alt_phone": doc.get("alt_phone"),
        "email": doc.get("email"),
        "address": doc.get("address"),
        "aadhaar_or_id": doc.get("aadhaar_or_id"),
        "photo_url": doc.get("photo_url"),
        "nominee_name": doc.get("nominee_name"),
        "nominee_relation": doc.get("nominee_relation"),
        "nominee_phone": doc.get("nominee_phone"),

        "site_visit_date": doc.get("site_visit_date"),
        "site_visit_verified": doc.get("site_visit_verified", True),
        "site_visit_notes": doc.get("site_visit_notes"),

        "venture_name": doc.get("venture_name", ""),
        "plot_number": doc.get("plot_number", ""),
        "plot_size": doc.get("plot_size"),
        "plot_facing": doc.get("plot_facing"),
        "rate_per_sq_yd": doc.get("rate_per_sq_yd"),
        "total_site_value": doc.get("total_site_value"),

        "supported_by": doc.get("supported_by"),
        "director_name": doc.get("director_name"),
        "agent_name": doc.get("agent_name"),

        "advance_amount": doc.get("advance_amount", "0"),
        "advance_amount_words": doc.get("advance_amount_words"),
        "payment_mode": doc.get("payment_mode", "UPI / Online Transfer"),
        "transaction_id": doc.get("transaction_id"),
        "payment_date": doc.get("payment_date") or created_str,
        "receipt_url": doc.get("receipt_url"),
        "balance_amount": doc.get("balance_amount"),
        "balance_due_date": doc.get("balance_due_date"),

        "verification_status": doc.get("verification_status", "Verified & Approved by ARK Infra"),
        "verified_by": doc.get("verified_by", "ARK Infra Management & MD/CEO Desk"),
        "remarks": doc.get("remarks"),
        "created_at": created,
        "updated_at": updated
    }

@router.get("", response_model=List[SiteApplicationResponse])
async def list_site_applications(
    venture: Optional[str] = Query(None, description="Filter by venture"),
    search: Optional[str] = Query(None, description="Search by customer, phone, plot, app no, etc."),
    current_admin: dict = Depends(get_current_admin)
):
    """Admin: Lists all customer site booking applications with permanent MongoDB records."""
    app_col = get_collection("site_applications")
    query = {}
    if venture and venture.lower() != "all":
        query["venture_name"] = venture

    if search:
        query["$or"] = [
            {"customer_name": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}},
            {"plot_number": {"$regex": search, "$options": "i"}},
            {"application_no": {"$regex": search, "$options": "i"}},
            {"venture_name": {"$regex": search, "$options": "i"}},
            {"supported_by": {"$regex": search, "$options": "i"}}
        ]

    cursor = app_col.find(query).sort("created_at", -1)
    docs = await cursor.to_list(length=1000)
    return [_format_app(d) for d in docs]

@router.post("", response_model=SiteApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_site_application(payload: SiteApplicationCreate, current_admin: dict = Depends(get_current_admin)):
    """Admin: Creates and permanently saves an official customer site application and advance payment."""
    app_col = get_collection("site_applications")
    customers_col = get_collection("customers")

    now = datetime.now(timezone.utc)
    doc = payload.model_dump()
    doc["created_at"] = now
    doc["updated_at"] = now

    if not doc.get("application_no"):
        count = await app_col.count_documents({}) + 1
        doc["application_no"] = f"ARK-APP-{datetime.now().strftime('%Y')}-{count:04d}"

    res = await app_col.insert_one(doc)
    doc["_id"] = res.inserted_id

    # If linked to an existing customer lead, update that customer's advance and status in MongoDB
    if payload.customer_id and ObjectId.is_valid(payload.customer_id):
        cust_update = {
            "advance_amount": payload.advance_amount,
            "site_visit_status": "Amount Paid",
            "project_interested": payload.venture_name,
            "plot_number": payload.plot_number,
            "plot_size": payload.plot_size or "",
            "supported_by": payload.supported_by,
            "updated_at": now
        }
        if payload.receipt_url:
            cust_update["receipt_url"] = payload.receipt_url
        if payload.photo_url:
            cust_update["photo_or_id"] = payload.photo_url
        await customers_col.update_one({"_id": ObjectId(payload.customer_id)}, {"$set": cust_update})

    return _format_app(doc)

@router.get("/{id}", response_model=SiteApplicationResponse)
async def get_site_application(id: str, current_admin: dict = Depends(get_current_admin)):
    """Admin: Retrieves a specific site application record."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Application ID format.")
    app_col = get_collection("site_applications")
    doc = await app_col.find_one({"_id": ObjectId(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Site Application not found.")
    return _format_app(doc)

@router.put("/{id}", response_model=SiteApplicationResponse)
async def update_site_application(id: str, payload: SiteApplicationUpdate, current_admin: dict = Depends(get_current_admin)):
    """Admin: Updates an existing customer site booking application."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Application ID format.")
    app_col = get_collection("site_applications")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    now = datetime.now(timezone.utc)
    update_data["updated_at"] = now

    res = await app_col.update_one({"_id": ObjectId(id)}, {"$set": update_data})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Site Application not found.")

    doc = await app_col.find_one({"_id": ObjectId(id)})

    # Also sync updated info back to linked customer if present
    cust_id = doc.get("customer_id")
    if cust_id and ObjectId.is_valid(cust_id):
        customers_col = get_collection("customers")
        cust_sync = {"updated_at": now}
        if "advance_amount" in update_data:
            cust_sync["advance_amount"] = update_data["advance_amount"]
        if "receipt_url" in update_data:
            cust_sync["receipt_url"] = update_data["receipt_url"]
        if "supported_by" in update_data:
            cust_sync["supported_by"] = update_data["supported_by"]
        await customers_col.update_one({"_id": ObjectId(cust_id)}, {"$set": cust_sync})

    return _format_app(doc)

@router.delete("/{id}")
async def delete_site_application(id: str, current_admin: dict = Depends(get_current_admin)):
    """Admin: Deletes a site application record."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Application ID format.")
    app_col = get_collection("site_applications")
    res = await app_col.delete_one({"_id": ObjectId(id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Site Application not found.")
    return {"success": True, "message": "Site Application record deleted permanently from MongoDB."}

@router.get("/{id}/pdf")
async def download_site_application_pdf(id: str, current_admin: dict = Depends(get_current_admin)):
    """
    Generates and downloads the Official Authorized Application & Advance Booking Receipt PDF
    featuring Customer details, Passport photo, Venture/Plot specifics, Advance Payment Receipt,
    Official ARK Infra Stamp/Seal, and Signatures of MD and CEO.
    """
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Application ID format.")
    app_col = get_collection("site_applications")
    doc = await app_col.find_one({"_id": ObjectId(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Site Application not found.")

    app_dict = _format_app(doc)
    pdf_bytes = await generate_site_application_pdf(app_dict)

    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', app_dict.get("customer_name", "Customer"))
    app_no_safe = re.sub(r'[^a-zA-Z0-9_-]', '_', app_dict.get("application_no", "ARK"))
    filename = f"ARK_Infra_Application_{app_no_safe}_{safe_name}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )
