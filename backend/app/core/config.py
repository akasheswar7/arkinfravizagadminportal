import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "ARK Infra Backend API"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    # Database
    MONGODB_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "ark_infra_dev"
    MONGODB_DB_NAME: str = ""

    @property
    def db_name(self) -> str:
        return self.MONGODB_DB_NAME.strip() if self.MONGODB_DB_NAME else self.DATABASE_NAME

    # JWT Authentication
    JWT_SECRET: str = "ark_infra_dev_jwt_secret_key_8492018392183902"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 480

    # Seed Admin Account
    ADMIN_EMAIL: str = "admin@arkinfravizag.com"
    ADMIN_PASSWORD: str = "admin123"

    # Domains & CORS
    FRONTEND_URL: str = "http://localhost:3000"
    API_BASE_URL: str = "http://localhost:8000"
    ALLOWED_ORIGINS: str = "*"

    # Storage Settings
    STORAGE_MODE: str = "local"  # 'local' or 'cloud'
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 15

    # Cloud Storage (S3 / R2 / MinIO compatible)
    CLOUD_STORAGE_ENDPOINT: str = ""
    CLOUD_STORAGE_BUCKET: str = ""
    CLOUD_STORAGE_ACCESS_KEY: str = ""
    CLOUD_STORAGE_SECRET_KEY: str = ""
    CLOUD_STORAGE_PUBLIC_URL: str = ""

    # Google Cloud Storage (GCS)
    GCS_BUCKET_NAME: str = ""
    GCS_PROJECT_ID: str = ""
    GCS_CREDENTIALS_FILE: str = ""
    GCS_CREDENTIALS_JSON: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # WhatsApp API (Optional)
    WHATSAPP_API_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
        extra = "allow"

    @property
    def cors_origins(self) -> List[str]:
        if not self.ALLOWED_ORIGINS:
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

settings = Settings()
