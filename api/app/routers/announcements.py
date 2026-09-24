from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends
from app.core.database import get_collection
from app.core.security import get_current_admin
from app.schemas.announcement import AnnouncementCreate, AnnouncementUpdate, AnnouncementResponse

router = APIRouter(tags=["Announcements"])

def _format_announcement(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "title": doc.get("title", ""),
        "message": doc.get("message", ""),
        "start_date": doc.get("start_date"),
        "end_date": doc.get("end_date"),
        "active": doc.get("active", True),
        "created_at": doc.get("created_at", datetime.now(timezone.utc)),
        "updated_at": doc.get("updated_at")
    }

# ----------------- PUBLIC ENDPOINTS -----------------

@router.get("/public/announcements/active", response_model=Optional[AnnouncementResponse])
async def get_active_announcement():
    """Returns the current active announcement for the public homepage banner."""
    ann_col = get_collection("announcements")
    doc = await ann_col.find_one({"active": True}, sort=[("created_at", -1)])
    if not doc:
        return None
    return _format_announcement(doc)

# ----------------- ADMIN ENDPOINTS -----------------

@router.get("/admin/announcements", response_model=List[AnnouncementResponse])
async def list_announcements(current_admin: dict = Depends(get_current_admin)):
    """Admin: Lists all announcements."""
    ann_col = get_collection("announcements")
    cursor = ann_col.find().sort("created_at", -1)
    docs = await cursor.to_list(length=100)
    return [_format_announcement(d) for d in docs]

@router.post("/admin/announcements", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
async def create_announcement(payload: AnnouncementCreate, current_admin: dict = Depends(get_current_admin)):
    """Admin: Creates a new announcement."""
    ann_col = get_collection("announcements")
    now = datetime.now(timezone.utc)
    doc = payload.model_dump()
    doc["created_at"] = now
    doc["updated_at"] = now

    # If new announcement is active, optionally deactivate previous ones
    if doc.get("active"):
        await ann_col.update_many({"active": True}, {"$set": {"active": False}})

    res = await ann_col.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _format_announcement(doc)

@router.put("/admin/announcements/{id}", response_model=AnnouncementResponse)
async def update_announcement(id: str, payload: AnnouncementUpdate, current_admin: dict = Depends(get_current_admin)):
    """Admin: Updates an announcement."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Announcement ID format.")
    ann_col = get_collection("announcements")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    update_data["updated_at"] = datetime.now(timezone.utc)
    if update_data.get("active") is True:
        await ann_col.update_many({"active": True, "_id": {"$ne": ObjectId(id)}}, {"$set": {"active": False}})

    res = await ann_col.update_one({"_id": ObjectId(id)}, {"$set": update_data})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found.")

    doc = await ann_col.find_one({"_id": ObjectId(id)})
    return _format_announcement(doc)

@router.patch("/admin/announcements/{id}/toggle-active", response_model=AnnouncementResponse)
async def toggle_active_announcement(id: str, current_admin: dict = Depends(get_current_admin)):
    """Admin: Toggles activation state for an announcement."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Announcement ID format.")
    ann_col = get_collection("announcements")
    doc = await ann_col.find_one({"_id": ObjectId(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Announcement not found.")

    new_state = not doc.get("active", False)
    if new_state:
        # Deactivate all others
        await ann_col.update_many({"active": True}, {"$set": {"active": False}})

    await ann_col.update_one({"_id": ObjectId(id)}, {"$set": {"active": new_state, "updated_at": datetime.now(timezone.utc)}})
    updated = await ann_col.find_one({"_id": ObjectId(id)})
    return _format_announcement(updated)

@router.delete("/admin/announcements/{id}")
async def delete_announcement(id: str, current_admin: dict = Depends(get_current_admin)):
    """Admin: Deletes an announcement."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Announcement ID format.")
    ann_col = get_collection("announcements")
    res = await ann_col.delete_one({"_id": ObjectId(id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found.")
    return {"success": True, "message": "Announcement deleted."}
