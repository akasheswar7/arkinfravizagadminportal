from datetime import datetime, timezone
from typing import List
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends
from app.core.database import get_collection
from app.core.security import get_current_admin
from app.schemas.director import DirectorCreate, DirectorUpdate, DirectorResponse

router = APIRouter(tags=["Directors"])

def _format_director(doc: dict, agents_count: int = 0) -> dict:
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name", ""),
        "role": doc.get("role", "Director"),
        "profile_image": doc.get("profile_image", ""),
        "bio": doc.get("bio", ""),
        "quote": doc.get("quote"),
        "phone": doc.get("phone"),
        "email": doc.get("email"),
        "agents_count": agents_count,
        "created_at": doc.get("created_at", datetime.now(timezone.utc)),
        "updated_at": doc.get("updated_at", datetime.now(timezone.utc))
    }

# ----------------- PUBLIC ENDPOINTS -----------------

@router.get("/public/directors", response_model=List[DirectorResponse])
async def get_public_directors():
    """Returns all directors with their agents count for the public website."""
    directors_col = get_collection("directors")
    agents_col = get_collection("agents")

    cursor = directors_col.find().sort("created_at", 1)
    directors = await cursor.to_list(length=100)

    result = []
    for d in directors:
        d_id = str(d["_id"])
        agents_count = await agents_col.count_documents({"director_id": d_id})
        result.append(_format_director(d, agents_count))
    return result

@router.get("/public/directors/{id}", response_model=DirectorResponse)
async def get_public_director(id: str):
    """Returns a single director profile."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Director ID format.")
    directors_col = get_collection("directors")
    agents_col = get_collection("agents")

    director = await directors_col.find_one({"_id": ObjectId(id)})
    if not director:
        raise HTTPException(status_code=404, detail="Director not found.")

    agents_count = await agents_col.count_documents({"director_id": id})
    return _format_director(director, agents_count)

# ----------------- ADMIN ENDPOINTS -----------------

@router.get("/admin/directors", response_model=List[DirectorResponse])
async def list_admin_directors(current_admin: dict = Depends(get_current_admin)):
    """Admin: Lists all directors with their agent counts."""
    return await get_public_directors()

@router.post("/admin/directors", response_model=DirectorResponse, status_code=status.HTTP_201_CREATED)
async def create_director(payload: DirectorCreate, current_admin: dict = Depends(get_current_admin)):
    """Admin: Creates a new Director."""
    directors_col = get_collection("directors")
    now = datetime.now(timezone.utc)
    
    doc = payload.model_dump()
    doc["created_at"] = now
    doc["updated_at"] = now

    res = await directors_col.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _format_director(doc, 0)

@router.get("/admin/directors/{id}", response_model=DirectorResponse)
async def get_admin_director(id: str, current_admin: dict = Depends(get_current_admin)):
    """Admin: Retrieves a specific director."""
    return await get_public_director(id)

@router.put("/admin/directors/{id}", response_model=DirectorResponse)
async def update_director(id: str, payload: DirectorUpdate, current_admin: dict = Depends(get_current_admin)):
    """Admin: Updates an existing director."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Director ID format.")
    directors_col = get_collection("directors")
    agents_col = get_collection("agents")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    update_data["updated_at"] = datetime.now(timezone.utc)
    res = await directors_col.update_one({"_id": ObjectId(id)}, {"$set": update_data})
    
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Director not found.")

    director = await directors_col.find_one({"_id": ObjectId(id)})
    agents_count = await agents_col.count_documents({"director_id": id})
    return _format_director(director, agents_count)

@router.delete("/admin/directors/{id}")
async def delete_director(id: str, current_admin: dict = Depends(get_current_admin)):
    """
    Admin: Deletes a director.
    DELETE PROTECTION: Fails with a friendly explanation if agents are assigned to this director.
    """
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Director ID format.")
    directors_col = get_collection("directors")
    agents_col = get_collection("agents")

    director = await directors_col.find_one({"_id": ObjectId(id)})
    if not director:
        raise HTTPException(status_code=404, detail="Director not found.")

    # Check assigned agents
    assigned_agents_count = await agents_col.count_documents({"director_id": id})
    if assigned_agents_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete Director '{director.get('name')}'. This Director has {assigned_agents_count} assigned Agent(s). Please reassign or delete these Agents before removing this Director."
        )

    await directors_col.delete_one({"_id": ObjectId(id)})
    return {"success": True, "message": f"Director '{director.get('name')}' deleted successfully."}
