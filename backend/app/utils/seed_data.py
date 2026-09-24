import logging
from datetime import datetime, timezone
from app.core.config import settings
from app.core.database import get_collection
from app.core.security import hash_password

logger = logging.getLogger(__name__)

async def seed_initial_database():
    """
    Seeds initial admin, directors, agents, customers, gallery, and announcements
    if the database is currently empty. Preserves all existing data if already populated.
    """
    admins_col = get_collection("admins")
    directors_col = get_collection("directors")
    agents_col = get_collection("agents")
    customers_col = get_collection("customers")
    gallery_col = get_collection("gallery")
    ann_col = get_collection("announcements")

    now = datetime.now(timezone.utc)

    # 1. Admin Seed
    admin_count = await admins_col.count_documents({})
    if admin_count == 0:
        logger.info(f"Seeding default admin: {settings.ADMIN_EMAIL}")
        await admins_col.insert_one({
            "email": settings.ADMIN_EMAIL.lower().strip(),
            "username": "admin",
            "hashed_password": hash_password(settings.ADMIN_PASSWORD),
            "full_name": "ARK Infra Executive Admin",
            "role": "admin",
            "created_at": now
        })

    # 2. Directors Seed
    director_count = await directors_col.count_documents({})
    director_ids = []
    if director_count == 0:
        logger.info("Seeding initial ARK Infra Directors...")
        directors_data = [
            {
                "name": "Adari Ramakrishna",
                "role": "Managing Director",
                "profile_image": "images/md-ramakrishna.webp",
                "bio": "Adari Ramakrishna serves as the Managing Director of ARK Infra. He brings extensive expertise in land procurement, joint ventures, and strategic investments. His focus is on selecting high-growth locations and creating win-win propositions for both landowners and home buyers.",
                "quote": "We don't just facilitate property investments—we help families, businesses, and investors secure their future with confidence and trust.",
                "phone": "+91 98484 98070",
                "email": "md@arkinfravizag.com",
                "created_at": now,
                "updated_at": now
            },
            {
                "name": "Yenamadala Vignesh",
                "role": "Branch Director & Operations Head",
                "profile_image": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=600&q=80",
                "bio": "Yenamadala Vignesh oversees field operations, layouts development, and site management. His hands-on leadership ensures all project execution runs strictly on schedule and adheres to top-tier quality benchmarks.",
                "quote": "Every client interaction is an opportunity to build trust, provide clarity, and guide dreams toward the right address.",
                "phone": "+91 90145 50481",
                "email": "vignesh@arkinfravizag.com",
                "created_at": now,
                "updated_at": now
            },
            {
                "name": "Konathala Venkata Rao",
                "role": "Executive Director",
                "profile_image": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600&q=80",
                "bio": "Konathala Venkata Rao brings decades of experience guiding strategic acquisitions, investor alliances, and governance across coastal Andhra Pradesh growth corridors.",
                "quote": "Integrity and transparency form the bedrock of sustainable landmarks.",
                "phone": "+91 81255 47801",
                "email": "venkatarao@arkinfravizag.com",
                "created_at": now,
                "updated_at": now
            }
        ]
        res = await directors_col.insert_many(directors_data)
        director_ids = [str(_id) for _id in res.inserted_ids]
    else:
        docs = await directors_col.find().to_list(length=10)
        director_ids = [str(d["_id"]) for d in docs]

    # 3. Agents Seed
    agent_count = await agents_col.count_documents({})
    if agent_count == 0 and len(director_ids) >= 3:
        logger.info("Seeding initial Agents assigned to Directors...")
        agents_data = [
            # Under Director 1 (Adari Ramakrishna)
            {
                "full_name": "K. Suresh Varma",
                "profile_image": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&q=80",
                "phone": "+91 98481 12345",
                "director_id": director_ids[0],
                "team_head_name": "Adari Ramakrishna",
                "designation": "Senior Property Consultant",
                "created_at": now,
                "updated_at": now
            },
            {
                "full_name": "M. Satish Kumar",
                "profile_image": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=400&q=80",
                "phone": "+91 94402 33456",
                "director_id": director_ids[0],
                "team_head_name": "Adari Ramakrishna",
                "designation": "Layout Investment Advisor",
                "created_at": now,
                "updated_at": now
            },
            {
                "full_name": "P. Ramesh Naidu",
                "profile_image": "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=400&q=80",
                "phone": "+91 99890 44567",
                "director_id": director_ids[0],
                "team_head_name": "Adari Ramakrishna",
                "designation": "Commercial Layout Specialist",
                "created_at": now,
                "updated_at": now
            },

            # Under Director 2 (Yenamadala Vignesh)
            {
                "full_name": "V. Rajesh Reddy",
                "profile_image": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=400&q=80",
                "phone": "+91 98485 55678",
                "director_id": director_ids[1],
                "team_head_name": "Yenamadala Vignesh",
                "designation": "Site Visit Coordinator",
                "created_at": now,
                "updated_at": now
            },
            {
                "full_name": "B. Kiran Chowdary",
                "profile_image": "https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?w=400&q=80",
                "phone": "+91 97011 66789",
                "director_id": director_ids[1],
                "team_head_name": "Yenamadala Vignesh",
                "designation": "Residential Plot Executive",
                "created_at": now,
                "updated_at": now
            },
            {
                "full_name": "S. Durga Prasad",
                "profile_image": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=400&q=80",
                "phone": "+91 98660 77890",
                "director_id": director_ids[1],
                "team_head_name": "Yenamadala Vignesh",
                "designation": "Customer Relations Associate",
                "created_at": now,
                "updated_at": now
            },

            # Under Director 3 (Konathala Venkata Rao)
            {
                "full_name": "T. Harish",
                "profile_image": "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=400&q=80",
                "phone": "+91 99480 88901",
                "director_id": director_ids[2],
                "team_head_name": "Konathala Venkata Rao",
                "designation": "Senior Venture Executive",
                "created_at": now,
                "updated_at": now
            },
            {
                "full_name": "N. Sravan Kumar",
                "profile_image": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=400&q=80",
                "phone": "+91 91770 99012",
                "director_id": director_ids[2],
                "team_head_name": "Konathala Venkata Rao",
                "designation": "Plot Allotment Manager",
                "created_at": now,
                "updated_at": now
            }
        ]
        await agents_col.insert_many(agents_data)

    # 4. Customers Seed
    customer_count = await customers_col.count_documents({})
    if customer_count == 0:
        logger.info("Seeding initial Customers...")
        customers_data = [
            {
                "customer_name": "G. Venkata Ramana",
                "phone": "+91 98480 11223",
                "email": "ramana.g@gmail.com",
                "submission_date": now.strftime("%Y-%m-%d"),
                "site_visit_status": "Registration Completed",
                "project_interested": "Highway City (Tallapalem)",
                "notes": "Completed registration for East facing 200 sq yd plot.",
                "created_at": now,
                "updated_at": now
            },
            {
                "customer_name": "Ch. Sridevi",
                "phone": "+91 97000 22334",
                "email": "sridevi.ch@gmail.com",
                "submission_date": now.strftime("%Y-%m-%d"),
                "site_visit_status": "Site Visit Completed",
                "project_interested": "Education City - Phase 1 (Sabbavaram)",
                "notes": "Visited Sabbavaram layout on Sunday. Interested in corner plot.",
                "created_at": now,
                "updated_at": now
            },
            {
                "customer_name": "B. Anand Varma",
                "phone": "+91 99880 33445",
                "email": "anand.varma@outlook.com",
                "submission_date": now.strftime("%Y-%m-%d"),
                "site_visit_status": "Pending",
                "project_interested": "Sandal Valley (Anandapuram)",
                "notes": "Requested weekend site visit with family from Steel Plant.",
                "created_at": now,
                "updated_at": now
            },
            {
                "customer_name": "K. Srinivas Rao",
                "phone": "+91 94411 44556",
                "email": "ksrao.vizag@yahoo.com",
                "submission_date": now.strftime("%Y-%m-%d"),
                "site_visit_status": "Pending",
                "project_interested": "Belmonk Layout Premium",
                "notes": "Enquired about bank loan tie-ups and SBI approval.",
                "created_at": now,
                "updated_at": now
            },
            {
                "customer_name": "P. Lakshmi Narayana",
                "phone": "+91 98662 55667",
                "email": "plnarayana@gmail.com",
                "submission_date": now.strftime("%Y-%m-%d"),
                "site_visit_status": "Site Visit Completed",
                "project_interested": "Golden Acres (Bhogapuram)",
                "notes": "Reviewed master plan near airport corridor.",
                "created_at": now,
                "updated_at": now
            }
        ]
        await customers_col.insert_many(customers_data)

    # 5. Gallery Seed
    gallery_count = await gallery_col.count_documents({})
    if gallery_count == 0:
        logger.info("Seeding initial Gallery items...")
        gallery_data = [
            {
                "title": "Construction Site Visit & Layout Inspection",
                "image_url": "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=1200&q=80",
                "thumbnail_url": "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=400&q=80",
                "category": "Site Visits",
                "description": "Engineers and layout managers reviewing 40-foot blacktop road construction and storm water drains.",
                "is_published": True,
                "created_at": now,
                "updated_at": now
            },
            {
                "title": "Grand Project Launch & Foundation Ceremony",
                "image_url": "https://images.unsplash.com/photo-1511578314322-379afb476865?w=1200&q=80",
                "thumbnail_url": "https://images.unsplash.com/photo-1511578314322-379afb476865?w=400&q=80",
                "category": "Events",
                "description": "Official unveiling of Education City Phase 1 at Sabbavaram in the presence of investors.",
                "is_published": True,
                "created_at": now,
                "updated_at": now
            },
            {
                "title": "Plot Boundary & Masterplan Client Inspection",
                "image_url": "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?w=1200&q=80",
                "thumbnail_url": "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?w=400&q=80",
                "category": "Site Visits",
                "description": "Guided walkthrough for investors inspecting demarcated villa plots.",
                "is_published": True,
                "created_at": now,
                "updated_at": now
            },
            {
                "title": "ARK Infra Corporate Excellence Gala",
                "image_url": "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=1200&q=80",
                "thumbnail_url": "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=800&q=80",
                "category": "Milestones",
                "description": "Annual awards honoring top performing directors, field executives, and engineering milestones.",
                "is_published": True,
                "created_at": now,
                "updated_at": now
            },
            {
                "title": "VMRDA Layout Tree Plantation & Green Belt Drive",
                "image_url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=1200&q=80",
                "thumbnail_url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=600&q=80",
                "category": "Achievements",
                "description": "Planting avenue greenery and landscaped children's parks across our gated projects.",
                "is_published": True,
                "created_at": now,
                "updated_at": now
            }
        ]
        await gallery_col.insert_many(gallery_data)

    # 6. Announcements Seed
    ann_count = await ann_col.count_documents({})
    if ann_count == 0:
        logger.info("Seeding initial Announcement...")
        await ann_col.insert_one({
            "title": "Special Festival Spot Registration Offer",
            "message": "Special festive booking offer on VMRDA approved plots at Alakananda Highway City (Tallapalem) and Sabbavaram Education City. Instant spot registration with bank loan assistance available!",
            "start_date": now.strftime("%Y-%m-%d"),
            "end_date": None,
            "active": True,
            "created_at": now,
            "updated_at": now
        })
