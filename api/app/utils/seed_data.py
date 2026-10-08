import logging
from datetime import datetime, timezone
from app.core.config import settings
from app.core.database import get_collection
from app.core.security import hash_password

logger = logging.getLogger(__name__)

INITIAL_PROJECTS = [
    {
        "title": "Gokulavanam",
        "description": "A Premium Open Plot Venture near Anakapalle",
        "image_url": "images/gokulavanam.webp",
        "status": "Ongoing",
        "tag": "PLOTS",
        "location": "Anakapalle",
        "price": "₹12,500 / Sq. Yd",
        "layout_features": [
            "TLP Approved Layout",
            "Loan Facility Available",
            "Clear Title & Documentation",
            "Wide Roads & Well Planned Layout",
            "Pollution-Free Environment",
            "Ideal for Investment & Dream Home"
        ],
        "project_highlights": [
            "TLP Approved Layout",
            "Plot Price: ₹12,500/- Per Sq. Yard",
            "Special Payment Plan: 1st Payment ₹1 Lakh, 2nd Payment ₹2 Lakh",
            "Limited Period Offer!",
            "Contact: 81792 42683"
        ],
        "location_highlights": [
            "Near Anakapalle, Andhra Pradesh",
            "200 Meters from Collector Bungalow",
            "3 KM from NH-16",
            "6 KM from Collector Office",
            "7 KM from Anakapalle",
            "17 KM from Gajuwaka",
            "Adjacent to 400 Acres Auto Nagar SEZ",
            "Near MIMSE Park",
            "Rapidly Developing Investment Corridor"
        ],
        "is_published": True
    },
    {
        "title": "Alakananda - Highway City",
        "description": "VMRDA & AP RERA Approved Layout at Tallapalem",
        "image_url": "images/highway-city-layout.webp",
        "status": "Ongoing",
        "tag": "PLOTS",
        "location": "Tallapalem",
        "price": "Market Rate",
        "layout_features": [
            "APRERA Approved Layout",
            "VMRDA Approved Layout",
            "Gated Community, Attractive Arch",
            "Compound wall with total layout",
            "40' Feet Black Top Roads",
            "Electricity with Street Lighting",
            "Avenue Plantation",
            "Children Parks",
            "Spot Registrations",
            "Bank Loan Available",
            "100% Vaasthu and Clear title",
            "Drainage Facility"
        ],
        "project_highlights": [],
        "location_highlights": [],
        "is_published": True
    },
    {
        "title": "Education City - Phase 1",
        "description": "VMRDA Proposed Plotted Development at Sabbavaram",
        "image_url": "images/education-city-layout.webp",
        "status": "Ongoing",
        "tag": "PLOTS",
        "location": "Sabbavaram",
        "price": "Market Rate",
        "layout_features": [],
        "project_highlights": [
            "100 Meters Road Facing (Master Plan)",
            "40 Feet Black Top Roads",
            "Grand Entrance Arch",
            "Underground Drainage",
            "Underground Electrification",
            "Avenue Plantation",
            "Park",
            "Children Play Area",
            "24 Hrs security Provision",
            "VMRDA Norms Development",
            "100% Vasthu Layout",
            "Premium Gated Community",
            "Pollution free Environment"
        ],
        "location_highlights": [
            "Located between Sabbavaram 6 lane NH-16 & Raipur 6 lane NH-26",
            "0.5 km from Raipur 6 Lane NH-26",
            "2 km from Sabbavaram 6 Lane NH-16",
            "3 km from Pinagadi National Highway",
            "6 km from Damodaram Sanjivayya National University",
            "8 km from Indian Maritime University",
            "8 km from Indian Institute of Petroleum & Energy",
            "19 km from NAD Junction",
            "21 km from Airport",
            "25 km from Railway Station",
            "25 km from Anakapalli",
            "28 km from Health City"
        ],
        "is_published": True
    },
    {
        "title": "Sandal Valley",
        "description": "Premium Plotted Layout near Ballanki Junction at Anandapuram",
        "image_url": "images/sandal-valley.webp",
        "status": "Ongoing",
        "tag": "PLOTS",
        "location": "Anandapuram",
        "price": "Market Rate",
        "layout_features": [
            "VMRDA Approved Layout",
            "Gated Community with Grand Entry Arch",
            "40' and 30' Feet Blacktop Roads",
            "Electricity with Street Lighting",
            "Underground Drainage System",
            "Avenue Plantation & Green Parks",
            "100% Vaasthu & Clear Title",
            "Spot Registration & Bank Loan Facility"
        ],
        "project_highlights": [
            "Located in the High-Appreciation Zone of Anandapuram",
            "Fully gated community with 24/7 Security",
            "Beautifully landscaped children's parks"
        ],
        "location_highlights": [
            "Near Anandapuram Junction (NH-16)",
            "Close to prestigious schools and colleges",
            "25-minute drive to Vizag city center"
        ],
        "is_published": True
    },
    {
        "title": "Vaibhav Classic",
        "description": "Completed premium plotted venture at Gandigudam, Simhachalam",
        "image_url": "images/vaibhav-classic.webp",
        "status": "Completed",
        "tag": "PLOTS",
        "location": "Simhachalam",
        "price": "Completed",
        "layout_features": [
            "VMRDA Approved Gated Community",
            "Fully compound-walled layout",
            "40' Feet Blacktop Roads",
            "Overhead Water Tank & Water Pipelines",
            "Electricity with street lighting",
            "Children's play park with seating",
            "Clear title and immediate registration"
        ],
        "project_highlights": [
            "Completed venture ready for instant housing construction",
            "100% Vasthu compliant layout",
            "Scenic pollution-free environment at Simhachalam foothills"
        ],
        "location_highlights": [
            "Located at Gandigudam, Simhachalam",
            "Close to the historic Simhachalam Temple",
            "15 minutes drive to NAD Junction",
            "Easy connectivity to Gopalapatnam and Pendurthi"
        ],
        "is_published": True
    },
    {
        "title": "Belmonk Layout Premium",
        "description": "Elite gated plotted community starting at ₹23,000/- per Sq. Yd at Tagarapuvalasa",
        "image_url": "images/belmonk-layout-premium.webp",
        "status": "Ongoing",
        "tag": "VILLA PLOTS",
        "location": "Tagarapuvalasa",
        "price": "₹23,000 / Sq. Yd",
        "layout_features": [
            "VMRDA Approved premium gated community",
            "Grand Entrance Arch with security post",
            "Wide 40' Feet Blacktop Roads",
            "Underground drainage and underground cabling",
            "Fully secure compound wall for entire layout",
            "Overhead water storage tank"
        ],
        "project_highlights": [
            "Premium pricing at ₹23,000/- per Sq. Yd",
            "Designed for luxury villa constructions",
            "Extensive landscape parks and children's play areas"
        ],
        "location_highlights": [
            "Located along the fast-developing Tagarapuvalasa corridor",
            "Very close to the 6-lane National Highway (NH-16)",
            "Surrounded by residential villa developments"
        ],
        "is_published": True
    },
    {
        "title": "Sri Sampath Ganesh Nagar",
        "description": "Successfully completed plotted layout at Lankelapalem",
        "image_url": "images/sampath-ganesh-nagar.webp",
        "status": "Completed",
        "tag": "PLOTS",
        "location": "Lankelapalem",
        "price": "Completed",
        "layout_features": [
            "VMRDA approved gated community",
            "Completed layout with well-laid 40' blacktop roads",
            "Electricity network with street lights",
            "Underground drainage and layout protection wall",
            "Beautiful avenue plantations",
            "Spot registration with clean titles"
        ],
        "project_highlights": [
            "Fully completed venture ready for house construction",
            "Surrounded by fully inhabited residential areas",
            "Bank loan options available with top banks"
        ],
        "location_highlights": [
            "Located at Lankelapalem, Visakhapatnam",
            "Near Lankelapalem Junction and NH-16",
            "Minutes away from Lankelapalem industrial SEZ hubs",
            "Close to schools, hospitals, and shopping centers"
        ],
        "is_published": True
    },
    {
        "title": "Kodduru Venture - Anakapalli",
        "description": "Plotted gated community with swimming pool starting at ₹16,000/- per Sq. Yd",
        "image_url": "images/annakapalli-kodduru.webp",
        "status": "Ongoing",
        "tag": "LUXURY PLOTS",
        "location": "Anakapalli",
        "price": "₹16,000 / Sq. Yd",
        "layout_features": [
            "VMRDA Approved gated layout",
            "Grand entrance arch and security cabin",
            "Fully operational swimming pool for residents",
            "40' and 33' Feet Blacktop Roads",
            "Underground drainage and sewage treatment lines",
            "Overhead water tank and piped water supply to each plot"
        ],
        "project_highlights": [
            "Premium lifestyle amenities including swimming pool and clubhouse area",
            "Gated community with 24/7 security surveillance",
            "Attractive landscaping and children's park"
        ],
        "location_highlights": [
            "Located at Kodduru near Anakapalli",
            "Excellent connectivity to Anakapalli bypass road",
            "Quick access to Visakhapatnam-Chennai highway NH-16",
            "Close to upcoming industrial hubs"
        ],
        "is_published": True
    },
    {
        "title": "RTC Depot Backside Venture",
        "description": "Premium commercial & residential plots starting at ₹23,000/- per Sq. Yd at Kothavalasa",
        "image_url": "images/kothavalasa.webp",
        "status": "Ongoing",
        "tag": "COMMERCIAL",
        "location": "Kothavalasa",
        "price": "₹23,000 / Sq. Yd",
        "layout_features": [
            "VMRDA approved layout",
            "Grand entry arch and secure fencing",
            "40' and 33' Feet wide Blacktop Roads",
            "Electricity and modern street lighting network",
            "Underground drainage and sewage lanes",
            "Water connection facility for every plot"
        ],
        "project_highlights": [
            "Located directly behind Kothavalasa RTC Depot",
            "Premium pricing at ₹23,000/- per Sq. Yd",
            "Ideal for both commercial shops and premium residential homes"
        ],
        "location_highlights": [
            "Located right behind the RTC Bus Depot in Kothavalasa",
            "Excellent connectivity to Araku-Vizag highway road",
            "Walkable distance to local transit, markets, and railway station"
        ],
        "is_published": True
    },
    {
        "title": "Kokkirapalli Venture (Phase 1)",
        "description": "Premium residential layout starting at ₹16,000/- per Sq. Yd at Yelamanchili",
        "image_url": "images/kokkirapalli.webp",
        "status": "Ongoing",
        "tag": "PLOTS",
        "location": "Yelamanchili",
        "price": "₹16,000 / Sq. Yd",
        "layout_features": [
            "VMRDA Approved Layout",
            "Decorative Entrance Arch with security outpost",
            "40' Feet Blacktop Roads throughout the layout",
            "Underground drainage and waste management lines",
            "Electricity lines with streetlights installed",
            "Plantation on either side of roads"
        ],
        "project_highlights": [
            "Venture price of ₹16,000/- per Sq. Yd",
            "Clear title and spot registration",
            "100% Vaasthu layout with beautiful open spacing"
        ],
        "location_highlights": [
            "Located in Kokkirapalli near Yelamanchili",
            "Close to Yelamanchili railway station and town center",
            "15 minutes drive to Atchutapuram SEZ industrial corridor"
        ],
        "is_published": True
    },
    {
        "title": "Golden Acres - Bhogapuram",
        "description": "Elite plotted venture at Kopparla starting at ₹17,000/- per Sq. Yd near Airport",
        "image_url": "images/golden-acres.webp",
        "status": "Ongoing",
        "tag": "AIRPORT PLOTS",
        "location": "Bhogapuram",
        "price": "₹17,000 / Sq. Yd",
        "layout_features": [
            "VMRDA & AP RERA Approved premium gated community",
            "Attractive Entrance Gate with 24/7 security staff",
            "Wide 40' Feet Blacktop Roads",
            "Modern streetlights and electricity network",
            "Drainage and water lines pre-laid",
            "Avenue plantation and landscaped park zone"
        ],
        "project_highlights": [
            "Located at Kopparla in the fast-growing Bhogapuram region",
            "Launch price of ₹17,000/- per Sq. Yd",
            "Designed for high capital gains near the international airport"
        ],
        "location_highlights": [
            "Just 10 minutes drive from the upcoming Bhogapuram International Airport",
            "Direct connectivity to National Highway NH-16",
            "Close to premium beach resorts and educational institutions"
        ],
        "is_published": True
    },
    {
        "title": "Sri Muktha Gardens",
        "description": "Completed budget-friendly plots starting at ₹7,500/- per Sq. Yd at Desapathrunipalem",
        "image_url": "images/sri-muktha-gardens.webp",
        "status": "Completed",
        "tag": "BUDGET PLOTS",
        "location": "Desapathrunipalem",
        "price": "₹7,500 / Sq. Yd",
        "layout_features": [
            "VMRDA Approved plotted development",
            "Completed blacktop roads (40' and 33' feet)",
            "Well-developed drainage system",
            "Electricity lines and avenue plants",
            "Entire layout compound fencing",
            "Spot registration with immediate construction option"
        ],
        "project_highlights": [
            "Highly budget-friendly entry price of ₹7,500/- per Sq. Yd",
            "Ready for immediate registration and house construction",
            "Vaastu compliant plots with clear titles"
        ],
        "location_highlights": [
            "Located at Desapathrunipalem near steel plant zone",
            "Close to steel plant sector gate and NH-16",
            "Surrounded by schools, colleges, and transportation options"
        ],
        "is_published": True
    },
    {
        "title": "Kokkirapalli Venture (Phase 2)",
        "description": "Premium gated residential plots starting at ₹16,000/- per Sq. Yd at Yelamanchili",
        "image_url": "images/kokkirapalli-alternate.webp",
        "status": "Ongoing",
        "tag": "PLOTS",
        "location": "Yelamanchili",
        "price": "₹16,000 / Sq. Yd",
        "layout_features": [
            "VMRDA Approved Layout - Phase 2 extension",
            "Gated community with grand entry arch and compound wall",
            "Wide 40' and 33' blacktop roads",
            "Advanced drainage facilities and electricity grids",
            "Landscaped children parks and seating areas"
        ],
        "project_highlights": [
            "Extension phase with competitive pricing of ₹16,000/- per Sq. Yd",
            "High investment yield potential",
            "100% Vaasthu compliant layouts with immediate registration"
        ],
        "location_highlights": [
            "Located at Yelamanchili, Kokkirapalli corridor",
            "Easy access to Anakapalli-Yelamanchili National Highway",
            "Close to major educational academies and business zones"
        ],
        "is_published": True
    }
]

INITIAL_GALLERY = [
    {
        "title": "Construction Site Visit & Layout Inspection",
        "category": "Site Visits",
        "media_type": "site_visit",
        "image_url": "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=800&q=80",
        "thumbnail_url": "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=800&q=80",
        "description": "On-site layout inspection and engineering survey at prime location.",
        "is_published": True
    },
    {
        "title": "Project Grand Launch Event",
        "category": "Events",
        "media_type": "photo",
        "image_url": "https://images.unsplash.com/photo-1511578314322-379afb476865?w=800&q=80",
        "thumbnail_url": "https://images.unsplash.com/photo-1511578314322-379afb476865?w=800&q=80",
        "description": "Official venture launch celebration with directors & clients.",
        "is_published": True
    },
    {
        "title": "Client Layout Inspection & Walkthrough",
        "category": "Site Visits",
        "media_type": "site_visit",
        "image_url": "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?w=800&q=80",
        "thumbnail_url": "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?w=800&q=80",
        "description": "Guided layout tour and spot registration verification with buyers.",
        "is_published": True
    },
    {
        "title": "Corporate Gala & Annual Celebration",
        "category": "Events",
        "media_type": "photo",
        "image_url": "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=800&q=80",
        "thumbnail_url": "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=800&q=80",
        "description": "ARK Infra annual corporate meet & executive team milestone awards.",
        "is_published": True
    },
    {
        "title": "Gokulavanam Layout Aerial View",
        "category": "Site Visits",
        "media_type": "site_visit",
        "image_url": "images/gokulavanam.webp",
        "thumbnail_url": "images/gokulavanam.webp",
        "description": "Aerial progress view of Gokulavanam open plot venture at Anakapalle.",
        "is_published": True
    },
    {
        "title": "Alakananda Highway City Walkthrough Video",
        "category": "Videos",
        "media_type": "video",
        "image_url": "images/highway-city-layout.webp",
        "thumbnail_url": "images/highway-city-layout.webp",
        "video_url": "video.mp4",
        "description": "Complete video tour of Alakananda Highway City layout development.",
        "is_published": True
    }
]

async def seed_initial_database():
    """
    Ensures default admin exists and seeds initial projects & gallery items ONCE.
    Uses a system flag document so deleted items are NEVER re-inserted on cold restarts.
    """
    admins_col = get_collection("admins")
    projects_col = get_collection("projects")
    gallery_col = get_collection("gallery")
    system_col = get_collection("system_settings")
    now = datetime.now(timezone.utc)

    # Check if initial database seed has already been completed in history
    seed_flag = await system_col.find_one({"_id": "initial_seed_completed"})
    if seed_flag:
        logger.info("Database initial seed already performed. Skipping re-seeding.")
        # Ensure default admin exists
        admin_count = await admins_col.count_documents({})
        if admin_count == 0:
            await admins_col.insert_one({
                "email": settings.ADMIN_EMAIL.lower().strip(),
                "username": "admin",
                "hashed_password": hash_password(settings.ADMIN_PASSWORD),
                "full_name": "ARK Infra Executive Admin",
                "role": "admin",
                "created_at": now
            })
        return

    # First-Time Admin Seed
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

    # First-Time Projects Seed (Only if collection is empty)
    project_count = await projects_col.count_documents({})
    if project_count == 0:
        logger.info("First-time seed: populating initial 13 projects into MongoDB...")
        for p in INITIAL_PROJECTS:
            existing = await projects_col.find_one({"title": p["title"]})
            if not existing:
                doc = {**p, "created_at": now, "updated_at": now}
                await projects_col.insert_one(doc)

    # First-Time Gallery Seed (Only if collection is empty)
    gallery_count = await gallery_col.count_documents({})
    if gallery_count == 0:
        logger.info("First-time seed: populating initial gallery items into MongoDB...")
        for g in INITIAL_GALLERY:
            existing = await gallery_col.find_one({"title": g["title"]})
            if not existing:
                doc = {**g, "created_at": now, "updated_at": now}
                await gallery_col.insert_one(doc)

    # Mark initial seed as permanently completed
    await system_col.update_one(
        {"_id": "initial_seed_completed"},
        {"$set": {"_id": "initial_seed_completed", "completed_at": now}},
        upsert=True
    )
    logger.info("Initial database seeding finished and marked complete.")


