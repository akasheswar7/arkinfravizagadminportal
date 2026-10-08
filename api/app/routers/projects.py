from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends, Query
from app.core.database import get_collection
from app.core.security import get_current_admin
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter(tags=["Projects"])

def _format_project(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "title": doc.get("title", ""),
        "tag": doc.get("tag", "PLOTS"),
        "status": doc.get("status", "Ongoing"),
        "location": doc.get("location", ""),
        "price": doc.get("price", ""),
        "description": doc.get("description", ""),
        "image_url": doc.get("image_url", ""),
        "brochure_url": doc.get("brochure_url"),
        "layout_features": doc.get("layout_features", []),
        "project_highlights": doc.get("project_highlights", []),
        "location_highlights": doc.get("location_highlights", []),
        "is_published": doc.get("is_published", True),
        "created_at": doc.get("created_at", datetime.now(timezone.utc)),
        "updated_at": doc.get("updated_at", datetime.now(timezone.utc))
    }

# ----------------- PUBLIC ENDPOINTS -----------------

@router.get("/public/projects", response_model=List[ProjectResponse])
async def get_public_projects(status_filter: Optional[str] = Query(None)):
    """Returns published projects for the public projects page."""
    projects_col = get_collection("projects")
    query = {"is_published": True}

    if status_filter and status_filter.lower() != "all":
        query["status"] = {"$regex": f"^{status_filter}$", "$options": "i"}

    cursor = projects_col.find(query).sort("created_at", -1)
    docs = await cursor.to_list(length=100)
    return [_format_project(d) for d in docs]

# ----------------- ADMIN ENDPOINTS -----------------

@router.get("/admin/projects", response_model=List[ProjectResponse])
async def list_admin_projects(current_admin: dict = Depends(get_current_admin)):
    """Admin: Lists all projects (published and draft)."""
    projects_col = get_collection("projects")
    cursor = projects_col.find().sort("created_at", -1)
    docs = await cursor.to_list(length=200)
    return [_format_project(d) for d in docs]

@router.post("/admin/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, current_admin: dict = Depends(get_current_admin)):
    """Admin: Adds a new project."""
    projects_col = get_collection("projects")
    now = datetime.now(timezone.utc)
    doc = payload.model_dump()
    doc["created_at"] = now
    doc["updated_at"] = now

    res = await projects_col.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _format_project(doc)

@router.put("/admin/projects/{id}", response_model=ProjectResponse)
async def update_project(id: str, payload: ProjectUpdate, current_admin: dict = Depends(get_current_admin)):
    """Admin: Updates an existing project."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Project ID format.")
    projects_col = get_collection("projects")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    update_data["updated_at"] = datetime.now(timezone.utc)
    res = await projects_col.update_one({"_id": ObjectId(id)}, {"$set": update_data})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Project not found.")

    doc = await projects_col.find_one({"_id": ObjectId(id)})
    return _format_project(doc)

@router.patch("/admin/projects/{id}/toggle-published", response_model=ProjectResponse)
async def toggle_project_published(id: str, current_admin: dict = Depends(get_current_admin)):
    """Admin: Toggles published status for a project."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Project ID format.")
    projects_col = get_collection("projects")

    doc = await projects_col.find_one({"_id": ObjectId(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found.")

    new_state = not doc.get("is_published", True)
    await projects_col.update_one({"_id": ObjectId(id)}, {"$set": {"is_published": new_state, "updated_at": datetime.now(timezone.utc)}})
    updated = await projects_col.find_one({"_id": ObjectId(id)})
    return _format_project(updated)

@router.delete("/admin/projects/{id}")
async def delete_project(id: str, current_admin: dict = Depends(get_current_admin)):
    """Admin: Deletes a project."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Project ID format.")
    projects_col = get_collection("projects")
    res = await projects_col.delete_one({"_id": ObjectId(id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found.")
    return {"success": True, "message": "Project deleted."}
