from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Query, Response
from app.core.database import get_collection
from app.core.security import get_current_admin
from app.services.pdf_service import (
    generate_team_hierarchy_pdf,
    generate_director_pdf,
    generate_customers_pdf
)

router = APIRouter(prefix="/admin/reports", tags=["PDF Reports"])

@router.get("/team-pdf")
async def download_team_hierarchy_pdf(current_admin: dict = Depends(get_current_admin)):
    """
    Generates and downloads the Complete Team Hierarchy PDF Report:
    CEO -> Directors -> Assigned Agents with photos, contact, and bios.
    """
    directors_col = get_collection("directors")
    agents_col = get_collection("agents")

    directors = await directors_col.find().sort("created_at", 1).to_list(length=100)
    agents = await agents_col.find().sort("full_name", 1).to_list(length=500)

    # Group agents by director_id
    agents_by_director = {}
    for a in agents:
        d_id = str(a.get("director_id", ""))
        if d_id not in agents_by_director:
            agents_by_director[d_id] = []
        agents_by_director[d_id].append(a)

    ceo_info = {
        "name": "Konathala Hanumantharao (Arun)",
        "role": "Chief Executive Officer (CEO)",
        "phone": "+91 81255 47801",
        "image": "images/ceo-arun.webp",
        "bio": "Overseeing ARK Infra's strategic vision, investor partnerships, and prime real estate expansion."
    }

    pdf_bytes = generate_team_hierarchy_pdf(directors, agents_by_director, ceo_info)
    filename = f"ARK_Infra_Team_Structure_{datetime.now().strftime('%Y%m%d')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/director-pdf/{director_id}")
async def download_director_pdf(director_id: str, current_admin: dict = Depends(get_current_admin)):
    """
    Generates and downloads a Director-Specific PDF Report:
    Selected Director's photo, bio, direct contact, plus all their assigned agents.
    """
    if not ObjectId.is_valid(director_id):
        raise HTTPException(status_code=400, detail="Invalid Director ID format.")
    
    directors_col = get_collection("directors")
    agents_col = get_collection("agents")

    director = await directors_col.find_one({"_id": ObjectId(director_id)})
    if not director:
        raise HTTPException(status_code=404, detail="Director not found.")

    agents = await agents_col.find({"director_id": director_id}).sort("full_name", 1).to_list(length=200)

    pdf_bytes = generate_director_pdf(director, agents)
    safe_name = director.get("name", "Director").replace(" ", "_")
    filename = f"ARK_Infra_Team_{safe_name}_{datetime.now().strftime('%Y%m%d')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/customers-pdf")
async def download_customers_pdf(
    status: str = Query("All", description="Status filter: All, Pending, Site Visit Completed, Registration Completed"),
    current_admin: dict = Depends(get_current_admin)
):
    """
    Generates and downloads the Customer Leads & Site Visits Status PDF Report.
    """
    customers_col = get_collection("customers")
    query = {}
    if status and status.lower() != "all":
        query["site_visit_status"] = status

    customers = await customers_col.find(query).sort("created_at", -1).to_list(length=1000)

    pdf_bytes = generate_customers_pdf(customers, status)
    safe_status = status.replace(" ", "_")
    filename = f"ARK_Infra_Customers_{safe_status}_{datetime.now().strftime('%Y%m%d')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
