import logging
import urllib.parse
from typing import List, Optional
from bson import ObjectId
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends
from app.core.config import settings
from app.core.database import get_collection
from app.core.security import get_current_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/whatsapp", tags=["WhatsApp Announcements"])

class WhatsAppBroadcastRequest(BaseModel):
    director_id: Optional[str] = None  # None for all agents
    message: str = Field(..., min_length=1, max_length=2000)

@router.get("/teams")
async def get_whatsapp_teams(current_admin: dict = Depends(get_current_admin)):
    """Returns available directors and their agent count for team messaging."""
    directors_col = get_collection("directors")
    agents_col = get_collection("agents")

    directors = await directors_col.find().sort("name", 1).to_list(length=100)
    teams = []
    for d in directors:
        d_id = str(d["_id"])
        count = await agents_col.count_documents({"director_id": d_id})
        teams.append({
            "director_id": d_id,
            "director_name": d.get("name"),
            "agent_count": count
        })
    return teams

@router.post("/prepare-broadcast")
async def prepare_whatsapp_broadcast(
    payload: WhatsAppBroadcastRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Prepares a team broadcast message:
    - If official WhatsApp API token is configured, can send via Meta Graph API.
    - Otherwise, generates direct click-to-chat WhatsApp URLs for each agent.
    """
    agents_col = get_collection("agents")
    query = {}
    if payload.director_id and payload.director_id != "all":
        query["director_id"] = payload.director_id

    agents = await agents_col.find(query).to_list(length=500)
    
    encoded_msg = urllib.parse.quote(payload.message)
    recipients = []

    for a in agents:
        raw_phone = a.get("phone", "").replace(" ", "").replace("-", "").replace("+", "")
        # Normalize Indian numbers if needed
        clean_phone = raw_phone
        if len(clean_phone) == 10:
            clean_phone = "91" + clean_phone

        wa_url = f"https://wa.me/{clean_phone}?text={encoded_msg}" if clean_phone else None

        recipients.append({
            "agent_name": a.get("full_name"),
            "phone": a.get("phone"),
            "clean_phone": clean_phone,
            "whatsapp_link": wa_url
        })

    api_configured = bool(settings.WHATSAPP_API_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID)

    return {
        "success": True,
        "api_configured": api_configured,
        "total_recipients": len(recipients),
        "recipients": recipients,
        "sample_link": recipients[0]["whatsapp_link"] if recipients else None,
        "message": "Broadcast prepared. Direct WhatsApp dispatch links generated."
    }
