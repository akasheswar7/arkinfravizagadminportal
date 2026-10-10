import logging
import urllib.parse
from typing import List, Optional
import httpx
from bson import ObjectId
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends
from app.core.config import settings
from app.core.database import get_collection
from app.core.security import get_current_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/whatsapp", tags=["WhatsApp Announcements"])

class WhatsAppBroadcastRequest(BaseModel):
    director_id: Optional[str] = None  # None / "all" for all agents, or "customers_all", "customers_pending", etc.
    message: str = Field(..., min_length=1, max_length=2000)

class WhatsAppConfigUpdate(BaseModel):
    api_token: str = Field(..., description="Meta WhatsApp Cloud API Access Token")
    phone_number_id: str = Field(..., description="Meta WhatsApp Phone Number ID")

class GatewayConfigUpdate(BaseModel):
    instance_id: str = Field(..., description="UltraMsg Instance ID e.g. instance10283")
    token: str = Field(..., description="UltraMsg Token")

class GatewayBroadcastRequest(BaseModel):
    director_id: Optional[str] = "all_members"
    message: str = Field(..., min_length=1, max_length=2000)
    selected_phones: Optional[List[str]] = None

async def get_effective_whatsapp_creds():
    """Retrieves WhatsApp credentials from MongoDB system_settings, falling back to .env settings."""
    settings_col = get_collection("system_settings")
    doc = await settings_col.find_one({"key": "whatsapp_config"})
    if doc and doc.get("api_token") and doc.get("phone_number_id"):
        return doc.get("api_token").strip(), doc.get("phone_number_id").strip()
    return (settings.WHATSAPP_API_TOKEN or "").strip(), (settings.WHATSAPP_PHONE_NUMBER_ID or "").strip()

@router.get("/config")
async def get_whatsapp_config(current_admin: dict = Depends(get_current_admin)):
    """Returns whether WhatsApp Cloud API is configured (hiding token secret)."""
    token, phone_id = await get_effective_whatsapp_creds()
    is_configured = bool(token and phone_id)
    masked_token = (token[:6] + "..." + token[-4:]) if (token and len(token) > 10) else ("Configured" if token else "")
    return {
        "configured": is_configured,
        "phone_number_id": phone_id,
        "token_preview": masked_token
    }

@router.post("/config")
async def save_whatsapp_config(payload: WhatsAppConfigUpdate, current_admin: dict = Depends(get_current_admin)):
    """Saves Meta WhatsApp Cloud API credentials directly to database settings."""
    settings_col = get_collection("system_settings")
    await settings_col.update_one(
        {"key": "whatsapp_config"},
        {"$set": {
            "key": "whatsapp_config",
            "api_token": payload.api_token.strip(),
            "phone_number_id": payload.phone_number_id.strip()
        }},
        upsert=True
    )
    return {"success": True, "message": "WhatsApp Cloud API credentials saved successfully!"}

@router.get("/teams")
async def get_whatsapp_teams(current_admin: dict = Depends(get_current_admin)):
    """Returns available directors, teams, and customer segments for WhatsApp dispatch."""
    directors_col = get_collection("directors")
    agents_col = get_collection("agents")
    customers_col = get_collection("customers")

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

    total_directors = len(directors)
    total_agents = await agents_col.count_documents({})
    total_customers = await customers_col.count_documents({})
    pending_customers = await customers_col.count_documents({"site_visit_status": "Pending"})
    completed_customers = await customers_col.count_documents({"site_visit_status": "Site Visit Completed"})

    return {
        "teams": teams,
        "counts": {
            "total_directors": total_directors,
            "total_agents": total_agents,
            "total_members": total_directors + total_agents,
            "total_customers": total_customers
        },
        "customer_segments": {
            "total_customers": total_customers,
            "pending_customers": pending_customers,
            "completed_customers": completed_customers
        }
    }

async def _fetch_recipients(director_id: Optional[str]) -> list:
    """Helper to fetch recipient contacts based on selector (Directors, Agents, Teams, Customers)."""
    recipients = []
    
    if director_id and director_id.startswith("customers_"):
        customers_col = get_collection("customers")
        c_query = {}
        if director_id == "customers_pending":
            c_query = {"site_visit_status": "Pending"}
        elif director_id == "customers_completed":
            c_query = {"site_visit_status": "Site Visit Completed"}
        elif director_id == "customers_positive":
            c_query = {"site_visit_status": {"$in": ["Positive", "Registration Completed", "Amount Paid"]}}
            
        customers = await customers_col.find(c_query).to_list(length=1000)
        for c in customers:
            raw_phone = (c.get("phone") or "").replace(" ", "").replace("-", "").replace("+", "")
            clean_phone = raw_phone
            if len(clean_phone) == 10:
                clean_phone = "91" + clean_phone
            recipients.append({
                "id": str(c.get("_id")),
                "name": c.get("customer_name") or "Customer",
                "phone": c.get("phone") or "",
                "clean_phone": clean_phone,
                "type": "customer",
                "extra": c.get("project_interested") or "Customer Lead"
            })
    elif director_id == "directors_all":
        # All Directors Only
        directors_col = get_collection("directors")
        directors = await directors_col.find().sort("name", 1).to_list(length=100)
        for d in directors:
            raw_phone = (d.get("phone") or "").replace(" ", "").replace("-", "").replace("+", "")
            clean_phone = raw_phone
            if len(clean_phone) == 10:
                clean_phone = "91" + clean_phone
            recipients.append({
                "id": str(d.get("_id")),
                "name": d.get("name") or "Director",
                "phone": d.get("phone") or "",
                "clean_phone": clean_phone,
                "type": "director",
                "extra": d.get("role") or "Managing Director"
            })
    elif director_id in ["all_members", "all_directors_agents"]:
        # Company-Wide: All Directors + All Agents
        directors_col = get_collection("directors")
        directors = await directors_col.find().sort("name", 1).to_list(length=100)
        for d in directors:
            raw_phone = (d.get("phone") or "").replace(" ", "").replace("-", "").replace("+", "")
            clean_phone = raw_phone
            if len(clean_phone) == 10:
                clean_phone = "91" + clean_phone
            recipients.append({
                "id": str(d.get("_id")),
                "name": d.get("name") or "Director",
                "phone": d.get("phone") or "",
                "clean_phone": clean_phone,
                "type": "director",
                "extra": d.get("role") or "Director"
            })
        agents_col = get_collection("agents")
        agents = await agents_col.find().sort("full_name", 1).to_list(length=500)
        for a in agents:
            raw_phone = (a.get("phone") or "").replace(" ", "").replace("-", "").replace("+", "")
            clean_phone = raw_phone
            if len(clean_phone) == 10:
                clean_phone = "91" + clean_phone
            recipients.append({
                "id": str(a.get("_id")),
                "name": a.get("full_name") or "Agent",
                "phone": a.get("phone") or "",
                "clean_phone": clean_phone,
                "type": "agent",
                "extra": a.get("designation") or "Real Estate Agent"
            })
    elif director_id in ["agents_all", "all"]:
        # All Agents Only
        agents_col = get_collection("agents")
        agents = await agents_col.find().sort("full_name", 1).to_list(length=500)
        for a in agents:
            raw_phone = (a.get("phone") or "").replace(" ", "").replace("-", "").replace("+", "")
            clean_phone = raw_phone
            if len(clean_phone) == 10:
                clean_phone = "91" + clean_phone
            recipients.append({
                "id": str(a.get("_id")),
                "name": a.get("full_name") or "Agent",
                "phone": a.get("phone") or "",
                "clean_phone": clean_phone,
                "type": "agent",
                "extra": a.get("designation") or "Real Estate Agent"
            })
    else:
        # A specific director's team (Director + their agents)
        from bson import ObjectId
        directors_col = get_collection("directors")
        try:
            d_obj = await directors_col.find_one({"_id": ObjectId(director_id)})
            if d_obj:
                raw_phone = (d_obj.get("phone") or "").replace(" ", "").replace("-", "").replace("+", "")
                clean_phone = raw_phone
                if len(clean_phone) == 10:
                    clean_phone = "91" + clean_phone
                recipients.append({
                    "id": str(d_obj.get("_id")),
                    "name": d_obj.get("name") or "Director",
                    "phone": d_obj.get("phone") or "",
                    "clean_phone": clean_phone,
                    "type": "director",
                    "extra": f"Head: {d_obj.get('role') or 'Director'}"
                })
        except Exception:
            pass

        agents_col = get_collection("agents")
        agents = await agents_col.find({"director_id": director_id}).sort("full_name", 1).to_list(length=500)
        for a in agents:
            raw_phone = (a.get("phone") or "").replace(" ", "").replace("-", "").replace("+", "")
            clean_phone = raw_phone
            if len(clean_phone) == 10:
                clean_phone = "91" + clean_phone
            recipients.append({
                "id": str(a.get("_id")),
                "name": a.get("full_name") or "Agent",
                "phone": a.get("phone") or "",
                "clean_phone": clean_phone,
                "type": "agent",
                "extra": a.get("designation") or "Real Estate Agent"
            })
            
    return recipients

@router.post("/prepare-broadcast")
async def prepare_whatsapp_broadcast(
    payload: WhatsAppBroadcastRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """Prepares formatted direct dispatch WhatsApp links for all matching recipients."""
    recipients_raw = await _fetch_recipients(payload.director_id)
    encoded_msg = urllib.parse.quote(payload.message)
    recipients = []

    for r in recipients_raw:
        clean_phone = r["clean_phone"]
        wa_url = f"https://wa.me/{clean_phone}?text={encoded_msg}" if clean_phone else None
        recipients.append({
            "agent_name": r["name"],
            "phone": r["phone"],
            "clean_phone": clean_phone,
            "extra": r["extra"],
            "type": r["type"],
            "whatsapp_link": wa_url
        })

    token, phone_id = await get_effective_whatsapp_creds()
    api_configured = bool(token and phone_id)

    return {
        "success": True,
        "api_configured": api_configured,
        "total_recipients": len(recipients),
        "recipients": recipients,
        "sample_link": recipients[0]["whatsapp_link"] if recipients else None,
        "group_share_link": f"https://api.whatsapp.com/send?text={encoded_msg}",
        "message": f"Broadcast prepared for {len(recipients)} recipients."
    }

@router.post("/send-cloud-broadcast")
async def send_meta_cloud_broadcast(
    payload: WhatsAppBroadcastRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Sends automated 1-click bulk WhatsApp messages via Official Meta WhatsApp Cloud API.
    """
    token, phone_id = await get_effective_whatsapp_creds()
    if not token or not phone_id:
        raise HTTPException(
            status_code=400,
            detail="Meta WhatsApp Cloud API is not configured yet. Please configure your Access Token and Phone Number ID."
        )

    recipients = await _fetch_recipients(payload.director_id)
    if not recipients:
        return {"success": True, "total": 0, "sent": 0, "failed": 0, "message": "No recipients found for selection."}

    meta_url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    sent_count = 0
    failed_count = 0
    errors = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        for r in recipients:
            target_number = r["clean_phone"]
            if not target_number:
                failed_count += 1
                continue

            body = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": target_number,
                "type": "text",
                "text": {
                    "preview_url": True,
                    "body": payload.message
                }
            }

            try:
                resp = await client.post(meta_url, headers=headers, json=body)
                if resp.status_code in [200, 201]:
                    sent_count += 1
                else:
                    failed_count += 1
                    err_json = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                    errors.append(f"{r['name']} ({target_number}): {err_json}")
            except Exception as e:
                failed_count += 1
                errors.append(f"{r['name']} ({target_number}): {str(e)}")

    return {
        "success": True,
        "total": len(recipients),
        "sent": sent_count,
        "failed": failed_count,
        "sample_errors": errors[:5],
        "message": f"Cloud broadcast finished: {sent_count} sent successfully, {failed_count} failed."
    }

@router.get("/gateway-config")
async def get_gateway_config(current_admin: dict = Depends(get_current_admin)):
    """Returns whether UltraMsg QR Gateway is configured."""
    settings_col = get_collection("system_settings")
    doc = await settings_col.find_one({"key": "ultramsg_config"})
    if doc and doc.get("instance_id") and doc.get("token"):
        inst = doc.get("instance_id").strip()
        tok = doc.get("token").strip()
        return {
            "configured": True,
            "instance_id": inst,
            "token_preview": (tok[:4] + "..." + tok[-4:]) if len(tok) > 8 else "***"
        }
    return {"configured": False, "instance_id": "", "token_preview": ""}

@router.get("/gateway-status")
async def get_gateway_status(current_admin: dict = Depends(get_current_admin)):
    """Pings UltraMsg instance to verify live WhatsApp linked device status."""
    settings_col = get_collection("system_settings")
    doc = await settings_col.find_one({"key": "ultramsg_config"})
    if not doc or not doc.get("instance_id") or not doc.get("token"):
        return {"configured": False, "connected": False, "message": "UltraMsg Gateway is not configured yet."}

    instance_id = doc["instance_id"].strip().rstrip("/")
    if not instance_id.startswith("instance") and instance_id.isdigit():
        instance_id = f"instance{instance_id}"
    token = doc["token"].strip()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"https://api.ultramsg.com/{instance_id}/instance/status", params={"token": token})
            if resp.status_code == 200:
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                status_info = data.get("status", {})
                account_info = status_info.get("accountStatus", {}) if isinstance(status_info, dict) else {}
                account_status = account_info.get("status") if isinstance(account_info, dict) else status_info.get("account_status")
                substatus = account_info.get("substatus") if isinstance(account_info, dict) else ""
                is_connected = bool(account_status == "authenticated" or substatus == "connected")
                qr_code = data.get("qrCode", "")
                return {
                    "configured": True,
                    "connected": is_connected,
                    "instance_id": instance_id,
                    "account_status": account_status or substatus or "authenticated",
                    "qr_code": qr_code,
                    "message": "Connected & Ready to Send!" if is_connected else f"Status: {account_status or substatus}"
                }
            else:
                return {
                    "configured": True,
                    "connected": False,
                    "instance_id": instance_id,
                    "message": f"UltraMsg response ({resp.status_code}): {resp.text[:120]}"
                }
    except Exception as e:
        return {
            "configured": True,
            "connected": False,
            "instance_id": instance_id,
            "message": f"Connection check failed: {str(e)}"
        }

@router.post("/gateway-config")
async def save_gateway_config(payload: GatewayConfigUpdate, current_admin: dict = Depends(get_current_admin)):
    """Saves UltraMsg QR Gateway instance credentials to database."""
    settings_col = get_collection("system_settings")
    clean_inst = payload.instance_id.strip().rstrip("/")
    if not clean_inst.startswith("instance") and clean_inst.isdigit():
        clean_inst = f"instance{clean_inst}"

    await settings_col.update_one(
        {"key": "ultramsg_config"},
        {"$set": {
            "key": "ultramsg_config",
            "instance_id": clean_inst,
            "token": payload.token.strip()
        }},
        upsert=True
    )
    return {"success": True, "message": "UltraMsg QR Gateway credentials saved successfully!"}

@router.post("/send-gateway-broadcast")
async def send_gateway_broadcast(
    payload: GatewayBroadcastRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Sends automated 100% background bulk WhatsApp messages via UltraMsg QR Gateway.
    Zero popups, zero tabs opened. Delivers directly into receivers' phones.
    """
    settings_col = get_collection("system_settings")
    doc = await settings_col.find_one({"key": "ultramsg_config"})
    if not doc or not doc.get("instance_id") or not doc.get("token"):
        raise HTTPException(
            status_code=400,
            detail="UltraMsg QR Gateway is not connected yet. Please connect your instance ID and Token."
        )

    instance_id = doc["instance_id"].strip().rstrip("/")
    if not instance_id.startswith("instance") and instance_id.isdigit():
        instance_id = f"instance{instance_id}"
    token = doc["token"].strip()

    recipients_raw = await _fetch_recipients(payload.director_id)

    # Filter to only checked / selected phone numbers from owner
    if payload.selected_phones is not None:
        recipients = [
            r for r in recipients_raw
            if r.get("clean_phone") in payload.selected_phones or r.get("phone") in payload.selected_phones
        ]
    else:
        recipients = recipients_raw

    if not recipients:
        return {"success": True, "total": 0, "sent": 0, "failed": 0, "message": "No matching contacts found."}

    ultramsg_url = f"https://api.ultramsg.com/{instance_id}/messages/chat"
    sent_count = 0
    failed_count = 0
    errors = []

    async with httpx.AsyncClient(timeout=20.0) as client:
        for r in recipients:
            target_number = r.get("clean_phone")
            if not target_number:
                failed_count += 1
                continue

            # Ensure proper international format with plus or standard without plus
            target_to = target_number if target_number.startswith("+") else ("+" + target_number)

            data = {
                "token": token,
                "to": target_to,
                "body": payload.message
            }

            try:
                resp = await client.post(ultramsg_url, data=data)
                if resp.status_code in [200, 201]:
                    res_json = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    if res_json.get("sent") in ["true", True] or res_json.get("message") == "ok" or "id" in res_json or res_json.get("success") is True:
                        sent_count += 1
                    else:
                        failed_count += 1
                        errors.append(f"{r['name']}: {resp.text}")
                else:
                    failed_count += 1
                    errors.append(f"{r['name']}: {resp.text}")
            except Exception as e:
                failed_count += 1
                errors.append(f"{r['name']}: {str(e)}")

    return {
        "success": True,
        "total": len(recipients),
        "sent": sent_count,
        "failed": failed_count,
        "sample_errors": errors[:5],
        "message": f"Background broadcast finished: Delivered to {sent_count} contacts! ({failed_count} failed)"
    }


import time

class BridgeHeartbeatPayload(BaseModel):
    connected: bool = False
    phone: Optional[str] = None
    qr: Optional[str] = None
    activeJob: Optional[dict] = None
    lastResult: Optional[dict] = None

class BridgeCommandPayload(BaseModel):
    action: str  # "logout" or "bulk-send"
    phones: Optional[List[str]] = None
    message: Optional[str] = None
    delayMs: Optional[int] = 1500

@router.post("/bridge-heartbeat")
async def bridge_heartbeat(payload: BridgeHeartbeatPayload):
    """Receives live status & QR code from the local PC WhatsApp Gateway and returns any queued command."""
    settings_col = get_collection("system_settings")
    doc = await settings_col.find_one({"key": "local_wa_bridge"})
    pending_cmd = doc.get("pending_command") if doc else None

    update_fields = {
        "key": "local_wa_bridge",
        "connected": payload.connected,
        "phone": payload.phone,
        "qr": payload.qr,
        "activeJob": payload.activeJob,
        "updated_at": time.time(),
        "pending_command": None
    }
    if payload.lastResult is not None:
        update_fields["last_result"] = payload.lastResult

    await settings_col.update_one(
        {"key": "local_wa_bridge"},
        {"$set": update_fields},
        upsert=True
    )
    return {"success": True, "command": pending_cmd}

@router.get("/bridge-status")
async def bridge_status():
    """Returns live status & QR code of the local PC WhatsApp Gateway via cloud relay."""
    settings_col = get_collection("system_settings")
    doc = await settings_col.find_one({"key": "local_wa_bridge"})
    if not doc:
        return {"success": False, "online": False}

    age = time.time() - float(doc.get("updated_at") or 0)
    if age > 120:
        return {"success": False, "online": False, "age": age}

    return {
        "success": True,
        "online": True,
        "connected": bool(doc.get("connected")),
        "phone": doc.get("phone"),
        "qr": doc.get("qr"),
        "activeJob": doc.get("activeJob"),
        "lastResult": doc.get("last_result")
    }

@router.post("/bridge-command")
async def bridge_command(payload: BridgeCommandPayload):
    """Queues a command (bulk-send or logout) for the local PC WhatsApp Gateway."""
    settings_col = get_collection("system_settings")
    cmd = {
        "id": str(int(time.time() * 1000)),
        "action": payload.action,
        "phones": payload.phones or [],
        "message": payload.message or "",
        "delayMs": payload.delayMs or 1500
    }
    await settings_col.update_one(
        {"key": "local_wa_bridge"},
        {"$set": {"pending_command": cmd, "last_result": None}},
        upsert=True
    )
    return {"success": True, "command_id": cmd["id"], "message": f"Queued {payload.action} for WhatsApp Gateway."}

from fastapi.responses import HTMLResponse

@router.get("/gateway-dashboard", response_class=HTMLResponse)
async def gateway_dashboard():
    """Universal Cloud QR Dashboard that works on any laptop, PC, or mobile browser."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>ARK Infra - WhatsApp Gateway Engine</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    :root {
      --navy: #050d1a;
      --navy-card: #0c182c;
      --gold: #c9a962;
      --green: #25d366;
    }
    body {
      margin: 0;
      padding: 0;
      background: var(--navy);
      color: #fff;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      text-align: center;
    }
    .card {
      background: var(--navy-card);
      border: 1.5px solid var(--gold);
      border-radius: 14px;
      padding: 2.2rem;
      max-width: 480px;
      width: 90%;
      box-shadow: 0 10px 40px rgba(0,0,0,0.8), 0 0 30px rgba(201,169,98,0.2);
    }
    h1 { margin: 0 0 0.5rem 0; color: var(--gold); font-size: 1.6rem; }
    p { color: #cbd5e1; font-size: 0.9rem; line-height: 1.5; margin-bottom: 1.5rem; }
    .qr-box { background: #fff; padding: 12px; border-radius: 10px; display: inline-block; margin: 1rem 0; }
    .badge { display: inline-block; padding: 6px 14px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; margin-bottom: 1rem; }
    .badge-success { background: rgba(37,211,102,0.2); color: var(--green); border: 1px solid var(--green); }
    .badge-waiting { background: rgba(201,169,98,0.2); color: var(--gold); border: 1px solid var(--gold); }
    .btn { background: var(--gold); color: #000; border: none; padding: 8px 18px; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 0.9rem; margin-top: 1rem; }
    .btn-danger { background: #ef4444; color: #fff; }
  </style>
</head>
<body>
  <div class="card">
    <h1>📱 ARK Infra WhatsApp Gateway</h1>
    <p>100% Free Background Bulk Delivery Engine (Universal Cloud Bridge)</p>
    <div id="statusArea">
      <div class="badge badge-waiting">⏳ Checking Connection...</div>
    </div>
    <div id="qrArea" style="display:none;">
      <div class="qr-box">
        <img id="qrImg" src="" alt="Scan QR Code" style="width: 280px; height: 280px; display:block;">
      </div>
      <p style="font-size: 0.85rem; color: #94a3b8;">
        Open <b>WhatsApp</b> on your phone ➔ <b>Linked Devices</b> ➔ <b>Link a Device</b> ➔ Scan this code!
      </p>
    </div>
    <div id="connectedArea" style="display:none;">
      <div class="badge badge-success" id="connectedBadge">🟢 Connected &amp; Ready</div>
      <p style="color: #4ade80; font-size: 0.95rem;">
        Your WhatsApp is connected! You can now send bulk messages from your Admin Portal on any laptop or phone with 1-click.
      </p>
      <button class="btn btn-danger" onclick="logout()">Unlink / Connect Another Number</button>
    </div>
  </div>
  <script>
    async function checkStatus() {
      let data = null;
      try {
        const r = await fetch('/api/admin/whatsapp/bridge-status');
        if (r.ok) {
          const d = await r.json();
          if (d && d.online) data = d;
        }
      } catch (_) {}
      if (!data) {
        try {
          const r2 = await fetch('http://localhost:3300/status');
          if (r2.ok) data = await r2.json();
        } catch (_) {}
      }
      if (data) {
        if (data.connected) {
          document.getElementById('statusArea').style.display = 'none';
          document.getElementById('qrArea').style.display = 'none';
          document.getElementById('connectedArea').style.display = 'block';
          document.getElementById('connectedBadge').textContent = '🟢 Connected: +' + (data.phone || '');
        } else if (data.qr) {
          document.getElementById('statusArea').style.display = 'none';
          document.getElementById('connectedArea').style.display = 'none';
          document.getElementById('qrArea').style.display = 'block';
          document.getElementById('qrImg').src = data.qr;
        } else {
          document.getElementById('statusArea').style.display = 'block';
          document.getElementById('statusArea').innerHTML = '<div class="badge badge-waiting">⏳ Generating QR Code...</div>';
          document.getElementById('qrArea').style.display = 'none';
          document.getElementById('connectedArea').style.display = 'none';
        }
      } else {
        document.getElementById('statusArea').style.display = 'block';
        document.getElementById('statusArea').innerHTML = '<div class="badge" style="background:rgba(239,68,68,0.2);color:#f87171;">Gateway host computer is currently asleep/offline</div>';
        document.getElementById('qrArea').style.display = 'none';
        document.getElementById('connectedArea').style.display = 'none';
      }
    }
    async function logout() {
      if (!confirm('Are you sure you want to unlink this WhatsApp number?')) return;
      await fetch('/api/admin/whatsapp/bridge-command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'logout' })
      });
      alert('Unlinked! Generating new QR code...');
      setTimeout(checkStatus, 2000);
    }
    setInterval(checkStatus, 2500);
    checkStatus();
  </script>
</body>
</html>"""



