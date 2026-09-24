from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends, Query
from app.core.database import get_collection
from app.core.security import get_current_admin
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse

router = APIRouter(prefix="/admin/customers", tags=["Customer Leads & Site Visits"])

def _format_customer(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "customer_name": doc.get("customer_name", ""),
        "phone": doc.get("phone"),
        "email": doc.get("email"),
        "photo_or_id": doc.get("photo_or_id"),
        "submission_date": doc.get("submission_date") or datetime.now().strftime("%Y-%m-%d"),
        "site_visit_status": doc.get("site_visit_status", "Pending"),
        "project_interested": doc.get("project_interested"),
        "notes": doc.get("notes"),
        "created_at": doc.get("created_at", datetime.now(timezone.utc)),
        "updated_at": doc.get("updated_at", datetime.now(timezone.utc))
    }

@router.get("", response_model=List[CustomerResponse])
async def list_customers(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by Pending, Site Visit Completed, Registration Completed"),
    search: Optional[str] = Query(None, description="Search by customer name or phone"),
    current_admin: dict = Depends(get_current_admin)
):
    """Admin: Lists all customer records with status filter and text search."""
    customers_col = get_collection("customers")
    query = {}
    if status_filter and status_filter.lower() != "all":
        query["site_visit_status"] = status_filter
    if search:
        query["$or"] = [
            {"customer_name": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}
        ]

    cursor = customers_col.find(query).sort("created_at", -1)
    docs = await cursor.to_list(length=500)
    return [_format_customer(d) for d in docs]

@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(payload: CustomerCreate, current_admin: dict = Depends(get_current_admin)):
    """Admin: Creates a customer lead."""
    customers_col = get_collection("customers")
    now = datetime.now(timezone.utc)
    doc = payload.model_dump()
    doc["created_at"] = now
    doc["updated_at"] = now

    res = await customers_col.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _format_customer(doc)

@router.get("/{id}", response_model=CustomerResponse)
async def get_customer(id: str, current_admin: dict = Depends(get_current_admin)):
    """Admin: Gets a customer lead by ID."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Customer ID format.")
    customers_col = get_collection("customers")
    doc = await customers_col.find_one({"_id": ObjectId(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Customer not found.")
    return _format_customer(doc)

@router.put("/{id}", response_model=CustomerResponse)
async def update_customer(id: str, payload: CustomerUpdate, current_admin: dict = Depends(get_current_admin)):
    """Admin: Updates customer details or site visit status."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Customer ID format.")
    customers_col = get_collection("customers")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    update_data["updated_at"] = datetime.now(timezone.utc)
    res = await customers_col.update_one({"_id": ObjectId(id)}, {"$set": update_data})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found.")

    doc = await customers_col.find_one({"_id": ObjectId(id)})
    return _format_customer(doc)

@router.delete("/{id}")
async def delete_customer(id: str, current_admin: dict = Depends(get_current_admin)):
    """Admin: Deletes a customer record."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Customer ID format.")
    customers_col = get_collection("customers")
    res = await customers_col.delete_one({"_id": ObjectId(id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found.")
    return {"success": True, "message": "Customer record deleted."}
