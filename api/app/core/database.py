import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None
    _loop: any = None

db_manager = DatabaseManager()

async def connect_to_mongo():
    logger.info(f"Connecting to MongoDB at: {settings.MONGODB_URI.split('@')[-1] if '@' in settings.MONGODB_URI else settings.MONGODB_URI}")
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    db_manager.client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
    db_manager._loop = loop
    db_manager.db = db_manager.client[settings.db_name]

    # Verify connection
    try:
        await db_manager.client.admin.command('ping')
        logger.info(f"Connected to MongoDB successfully! Using database: '{settings.db_name}'")
        
        # Ensure collections & indexes
        await db_manager.db["admins"].create_index("email", unique=True)
        await db_manager.db["agents"].create_index("director_id")
        await db_manager.db["customers"].create_index("site_visit_status")
        await db_manager.db["gallery"].create_index("category")
        await db_manager.db["announcements"].create_index("active")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise e

async def close_mongo_connection():
    if db_manager.client:
        logger.info("Closing MongoDB connection...")
        db_manager.client.close()
        logger.info("MongoDB connection closed.")

def get_db() -> AsyncIOMotorDatabase:
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if db_manager.client is None or db_manager._loop != current_loop:
        db_manager.client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
        db_manager._loop = current_loop
        db_manager.db = db_manager.client[settings.db_name]
    return db_manager.db

def get_collection(name: str):
    db = get_db()
    return db[name]
