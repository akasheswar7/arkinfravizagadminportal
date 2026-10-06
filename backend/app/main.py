import os
import sys
import logging
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure backend directory is in sys.path for serverless environments (Vercel)
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
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
    projects,
    reports,
    stats,
    whatsapp,
    site_applications
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
    allow_origins=["*"],
    allow_origin_regex=r"^https?:\/\/.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__, "path": request.url.path}
    )

@app.middleware("http")
async def normalize_vercel_paths(request: Request, call_next):
    # Handle serverless path mapping if Vercel passes full script path
    path = request.scope.get("path", "")
    if path.startswith("/api/index.py"):
        sub = path[len("/api/index.py"):]
        request.scope["path"] = sub if sub else "/"
    return await call_next(request)

# Static Uploads directory for images (Vercel uses /tmp)
if os.environ.get("VERCEL"):
    UPLOAD_PATH = Path("/tmp") / settings.UPLOAD_DIR
else:
    UPLOAD_PATH = Path(__file__).resolve().parent.parent / settings.UPLOAD_DIR

try:
    UPLOAD_PATH.mkdir(parents=True, exist_ok=True)
    if not os.environ.get("VERCEL"):
        app.mount("/uploads", StaticFiles(directory=str(UPLOAD_PATH)), name="uploads")
except Exception as e:
    logger.warning(f"Static uploads mount warning: {e}")

# Mount Routers (Dual mounted under both /api and root to handle any proxy/rewrite configuration)
all_routers = [
    auth.router,
    uploads.router,
    directors.router,
    agents.router,
    customers.router,
    gallery.router,
    announcements.router,
    projects.router,
    reports.router,
    stats.router,
    whatsapp.router,
    site_applications.router
]

for r in all_routers:
    app.include_router(r, prefix=settings.API_PREFIX)
    app.include_router(r)

@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Health check endpoint for status monitoring."""
    return {
        "status": "healthy",
        "service": "ARK Infra Backend API",
        "database": settings.DATABASE_NAME,
        "storage_mode": settings.STORAGE_MODE
    }

@app.get("/api-debug")
@app.get("/api/api-debug")
async def debug_check(request: Request):
    return {
        "url": str(request.url),
        "path": request.url.path,
        "scope_path": request.scope.get("path"),
        "method": request.method
    }

from fastapi import Response, HTTPException
from app.services.storage_service import storage_service

@app.get("/uploads/{filename}")
@app.get("/api/uploads/{filename}")
async def serve_uploaded_file(filename: str):
    result = await storage_service.get_file(filename)
    if not result:
        raise HTTPException(status_code=404, detail="Photo not found")
    file_bytes, content_type = result
    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"}
    )
