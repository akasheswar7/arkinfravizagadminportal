from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends, Query
from app.core.database import get_collection
from app.core.security import get_current_admin
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse

router = APIRouter(tags=["Agents"])

def _format_agent(doc: dict, director_name: Optional[str] = None) -> dict:
    return {
        "id": str(doc["_id"]),
        "full_name": doc.get("full_name", ""),
        "profile_image": doc.get("profile_image", ""),
        "phone": doc.get("phone", ""),
        "director_id": str(doc.get("director_id", "")),
        "team_head_name": doc.get("team_head_name") or director_name or "Team Lead",
        "designation": doc.get("designation", "Real Estate Agent"),
        "email": doc.get("email"),
        "director_name": director_name or doc.get("team_head_name"),
        "created_at": doc.get("created_at", datetime.now(timezone.utc)),
        "updated_at": doc.get("updated_at", datetime.now(timezone.utc))
    }

# ----------------- PUBLIC ENDPOINTS -----------------

@router.get("/public/directors/{director_id}/agents", response_model=List[AgentResponse])
async def get_public_agents_by_director(director_id: str):
    """Returns all agents reporting under a specific Director for the public website."""
    agents_col = get_collection("agents")
    directors_col = get_collection("directors")

    director = None
    if ObjectId.is_valid(director_id):
        director = await directors_col.find_one({"_id": ObjectId(director_id)})

    director_name = director.get("name") if director else "Director"

    cursor = agents_col.find({"director_id": director_id}).sort("created_at", 1)
    agents = await cursor.to_list(length=200)

    return [_format_agent(a, director_name) for a in agents]

@router.get("/public/agents", response_model=List[AgentResponse])
async def get_all_public_agents():
    """Returns full agent directory for public reference."""
    agents_col = get_collection("agents")
    directors_col = get_collection("directors")

    # Map director IDs to names for quick reference
    directors_cursor = directors_col.find()
    directors = await directors_cursor.to_list(length=100)
    d_map = {str(d["_id"]): d.get("name", "Director") for d in directors}

    agents_cursor = agents_col.find().sort("full_name", 1)
    agents = await agents_cursor.to_list(length=300)

    return [_format_agent(a, d_map.get(str(a.get("director_id")), "Director")) for a in agents]

# ----------------- ADMIN ENDPOINTS -----------------

@router.get("/admin/agents", response_model=List[AgentResponse])
async def list_admin_agents(
    director_id: Optional[str] = Query(None, description="Filter agents by director"),
    search: Optional[str] = Query(None, description="Search by name or phone"),
    current_admin: dict = Depends(get_current_admin)
):
    """Admin: Lists all agents with director filtering and search."""
    agents_col = get_collection("agents")
    directors_col = get_collection("directors")

    directors = await directors_col.find().to_list(length=100)
    d_map = {str(d["_id"]): d.get("name", "Director") for d in directors}

    query = {}
    if director_id:
        query["director_id"] = director_id
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}
        ]

    cursor = agents_col.find(query).sort("created_at", -1)
    agents = await cursor.to_list(length=500)

    return [_format_agent(a, d_map.get(str(a.get("director_id")), "Director")) for a in agents]

@router.post("/admin/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(payload: AgentCreate, current_admin: dict = Depends(get_current_admin)):
    """Admin: Creates a new Agent assigned to a Director."""
    agents_col = get_collection("agents")
    directors_col = get_collection("directors")

    # Validate director existence
    director_name = "Director"
    if ObjectId.is_valid(payload.director_id):
        director = await directors_col.find_one({"_id": ObjectId(payload.director_id)})
        if not director:
            raise HTTPException(status_code=400, detail="The selected Director does not exist.")
        director_name = director.get("name", "Director")
    else:
        raise HTTPException(status_code=400, detail="Invalid Director ID.")

    now = datetime.now(timezone.utc)
    doc = payload.model_dump()
    if not doc.get("team_head_name"):
        doc["team_head_name"] = director_name
    doc["created_at"] = now
    doc["updated_at"] = now

    res = await agents_col.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _format_agent(doc, director_name)

@router.get("/admin/agents/{id}", response_model=AgentResponse)
async def get_admin_agent(id: str, current_admin: dict = Depends(get_current_admin)):
    """Admin: Gets a single agent."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Agent ID format.")
    agents_col = get_collection("agents")
    directors_col = get_collection("directors")

    agent = await agents_col.find_one({"_id": ObjectId(id)})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")

    director_name = "Director"
    if ObjectId.is_valid(agent.get("director_id", "")):
        d = await directors_col.find_one({"_id": ObjectId(agent["director_id"])})
        if d:
            director_name = d.get("name", "Director")

    return _format_agent(agent, director_name)

@router.put("/admin/agents/{id}", response_model=AgentResponse)
async def update_agent(id: str, payload: AgentUpdate, current_admin: dict = Depends(get_current_admin)):
    """Admin: Updates an agent, optionally reassigning them to another director."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Agent ID format.")
    agents_col = get_collection("agents")
    directors_col = get_collection("directors")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    if "director_id" in update_data:
        if ObjectId.is_valid(update_data["director_id"]):
            d = await directors_col.find_one({"_id": ObjectId(update_data["director_id"])})
            if not d:
                raise HTTPException(status_code=400, detail="Assigned Director does not exist.")
            if not update_data.get("team_head_name"):
                update_data["team_head_name"] = d.get("name")
        else:
            raise HTTPException(status_code=400, detail="Invalid Director ID format.")

    update_data["updated_at"] = datetime.now(timezone.utc)
    res = await agents_col.update_one({"_id": ObjectId(id)}, {"$set": update_data})
    
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found.")

    agent = await agents_col.find_one({"_id": ObjectId(id)})
    director_name = "Director"
    if ObjectId.is_valid(agent.get("director_id", "")):
        d = await directors_col.find_one({"_id": ObjectId(agent["director_id"])})
        if d:
            director_name = d.get("name", "Director")

    return _format_agent(agent, director_name)

@router.delete("/admin/agents/{id}")
async def delete_agent(id: str, current_admin: dict = Depends(get_current_admin)):
    """Admin: Deletes an agent."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid Agent ID format.")
    agents_col = get_collection("agents")
    res = await agents_col.delete_one({"_id": ObjectId(id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return {"success": True, "message": "Agent deleted successfully."}
