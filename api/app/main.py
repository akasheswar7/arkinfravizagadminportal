import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.utils.seed_data import seed_initial_database

from app.routers import (
    auth,
    uploads,
    directors,
    agents,
    customers,
    gallery,
    announcements,
    reports,
    stats,
    whatsapp
)

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ark_infra")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB & Seed if empty
    logger.info("Initializing ARK Infra Backend API...")
    try:
        await connect_to_mongo()
        await seed_initial_database()
    except Exception as e:
        logger.warning(f"Database startup connection notice: {e}")
    yield
    # Shutdown: Close MongoDB connection
    try:
        await close_mongo_connection()
    except Exception:
        pass

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production Dynamic CMS & Executive Admin Backend for ARK Infra.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
origins = settings.cors_origins
logger.info(f"Configuring CORS with origins: {origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if "*" not in origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Uploads directory for images (Vercel uses /tmp)
if os.environ.get("VERCEL"):
    UPLOAD_PATH = Path("/tmp") / settings.UPLOAD_DIR
else:
    UPLOAD_PATH = Path(__file__).resolve().parent.parent / settings.UPLOAD_DIR

try:
    UPLOAD_PATH.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_PATH)), name="uploads")
except Exception as e:
    logger.warning(f"Static uploads mount warning: {e}")

# Mount Routers under /api
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(uploads.router, prefix=settings.API_PREFIX)
app.include_router(directors.router, prefix=settings.API_PREFIX)
app.include_router(agents.router, prefix=settings.API_PREFIX)
app.include_router(customers.router, prefix=settings.API_PREFIX)
app.include_router(gallery.router, prefix=settings.API_PREFIX)
app.include_router(announcements.router, prefix=settings.API_PREFIX)
app.include_router(reports.router, prefix=settings.API_PREFIX)
app.include_router(stats.router, prefix=settings.API_PREFIX)
app.include_router(whatsapp.router, prefix=settings.API_PREFIX)

@app.get("/api/health")
async def health_check():
    """Health check endpoint for status monitoring."""
    return {
        "status": "healthy",
        "service": "ARK Infra Backend API",
        "database": settings.DATABASE_NAME,
        "storage_mode": settings.STORAGE_MODE
    }
