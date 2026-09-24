from fastapi import APIRouter, Depends
from app.core.database import get_collection
from app.core.security import get_current_admin

router = APIRouter(prefix="/admin/stats", tags=["Admin Statistics"])

@router.get("")
async def get_dashboard_stats(current_admin: dict = Depends(get_current_admin)):
    """Provides high-level dashboard metrics for the admin overview."""
    directors_col = get_collection("directors")
    agents_col = get_collection("agents")
    customers_col = get_collection("customers")
    gallery_col = get_collection("gallery")
    ann_col = get_collection("announcements")

    total_directors = await directors_col.count_documents({})
    total_agents = await agents_col.count_documents({})
    total_customers = await customers_col.count_documents({})
    pending_visits = await customers_col.count_documents({"site_visit_status": "Pending"})
    completed_visits = await customers_col.count_documents({"site_visit_status": "Site Visit Completed"})
    registrations = await customers_col.count_documents({"site_visit_status": "Registration Completed"})
    gallery_items = await gallery_col.count_documents({})
    active_announcements = await ann_col.count_documents({"active": True})

    return {
        "total_directors": total_directors,
        "total_agents": total_agents,
        "total_customers": total_customers,
        "pending_site_visits": pending_visits,
        "completed_site_visits": completed_visits,
        "registrations": registrations,
        "gallery_items": gallery_items,
        "active_announcements": active_announcements
    }
