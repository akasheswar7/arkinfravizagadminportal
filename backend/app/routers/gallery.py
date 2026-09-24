from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends, Query
from app.core.database import get_collection
from app.core.security import get_current_admin
from app.schemas.gallery import GalleryCreate, GalleryUpdate, GalleryResponse

router = APIRouter(tags=["Gallery"])

def _format_gallery(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "title": doc.get("title", ""),
        "image_url": doc.get("image_url", ""),
        "thumbnail_url": doc.get("thumbnail_url") or doc.get("image_url"),
        "category": doc.get("category", "Events"),
        "description": doc.get("description"),
        "is_published": doc.get("is_published", True),
        "created_at": doc.get("created_at", datetime.now(timezone.utc)),
        "updated_at": doc.get("updated_at", datetime.now(timezone.utc))
    }

# ----------------- PUBLIC ENDPOINTS -----------------

@router.get("/public/gallery", response_model=List[GalleryResponse])
async def get_public_gallery(category: Optional[str] = Query(None)):
    """Returns published gallery items for the public gallery page."""
    gallery_col = get_collection("gallery")
    query = {"is_published": True}

    if category and category.lower() != "all":
        # Handle matching for both standard categories and legacy 'site' / 'event' tags
        if category.lower() == "site":
            query["$or"] = [{"category": "Site Visits"}, {"category": "site"}, {"category": "Projects"}]
        elif category.lower() == "event":
            query["$or"] = [{"category": "Events"}, {"category": "event"}, {"category": "Milestones"}, {"category": "Achievements"}]
        else:
            query["category"] = {"$regex": f"^{category}$", "$options": "i"}

    cursor = gallery_col.find(query).sort("created_at", -1)
    docs = await cursor.to_list(length=200)
    return [_format_gallery(d) for d in docs]

# ----------------- ADMIN ENDPOINTS -----------------

@router.get("/admin/gallery", response_model=List[GalleryResponse])
async def list_admin_gallery(
    category: Optional[str] = Query(None),
    current_admin: dict = Depends(get_current_admin)
):
    """Admin: Lists all gallery photos."""
    gallery_col = get_collection("gallery")
    query = {}
    if category and category.lower() != "all":
        query["category"] = category

    cursor = gallery_col.find(query).sort("created_at", -1)
    docs = await cursor.to_list(length=300)
    return [_format_gallery(d) for d in docs]

@router.post("/admin/gallery", response_model=GalleryResponse, status_code=status.HTTP_201_CREATED)
async def create_gallery_item(payload: GalleryCreate, current_admin: dict = Depends(get_current_admin)):
    """Admin: Adds a photo to the gallery."""
    gallery_col = get_collection("gallery")
    now = datetime.now(timezone.utc)
    doc = payload.model_dump()
    doc["created_at"] = now
    doc["updated_at"] = now

    res = await gallery_col.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _format_gallery(doc)

@router.put("/admin/gallery/{id}", response_model=GalleryResponse)
async def update_gallery_item(id: str, payload: GalleryUpdate, current_admin: dict = Depends(get_current_admin)):
    """Admin: Updates a gallery item."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Gallery ID format.")
    gallery_col = get_collection("gallery")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    update_data["updated_at"] = datetime.now(timezone.utc)
    res = await gallery_col.update_one({"_id": ObjectId(id)}, {"$set": update_data})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Gallery item not found.")

    doc = await gallery_col.find_one({"_id": ObjectId(id)})
    return _format_gallery(doc)

@router.delete("/admin/gallery/{id}")
async def delete_gallery_item(id: str, current_admin: dict = Depends(get_current_admin)):
    """Admin: Deletes a gallery item."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Gallery ID format.")
    gallery_col = get_collection("gallery")
    res = await gallery_col.delete_one({"_id": ObjectId(id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Gallery item not found.")
    return {"success": True, "message": "Gallery item deleted."}
