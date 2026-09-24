import os
import logging
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)

# Ensure upload directory exists locally
UPLOAD_PATH = Path(__file__).resolve().parent.parent.parent / settings.UPLOAD_DIR
UPLOAD_PATH.mkdir(parents=True, exist_ok=True)

class StorageService:
    def __init__(self):
        self.mode = settings.STORAGE_MODE
        self.upload_dir = UPLOAD_PATH
        logger.info(f"StorageService initialized in '{self.mode}' mode. Local path: {self.upload_dir}")

    async def save_file(self, file_bytes: bytes, filename: str, content_type: str = "image/webp") -> str:
        """
        Saves file either locally or to cloud object storage.
        Returns the accessible URL for the saved file.
        """
        if self.mode == "cloud":
            # 1. Native Google Cloud Storage (GCS)
            gcs_bucket = settings.GCS_BUCKET_NAME
            if gcs_bucket:
                try:
                    import json
                    from google.cloud import storage as gcs
                    client = None
                    if settings.GCS_CREDENTIALS_JSON:
                        creds = json.loads(settings.GCS_CREDENTIALS_JSON)
                        client = gcs.Client.from_service_account_info(creds)
                    elif settings.GCS_CREDENTIALS_FILE and os.path.exists(settings.GCS_CREDENTIALS_FILE):
                        client = gcs.Client.from_service_account_json(settings.GCS_CREDENTIALS_FILE)
                    elif settings.GOOGLE_APPLICATION_CREDENTIALS and os.path.exists(settings.GOOGLE_APPLICATION_CREDENTIALS):
                        client = gcs.Client.from_service_account_json(settings.GOOGLE_APPLICATION_CREDENTIALS)
                    else:
                        client = gcs.Client(project=settings.GCS_PROJECT_ID or None)

                    bucket = client.bucket(gcs_bucket)
                    blob = bucket.blob(filename)
                    blob.upload_from_string(file_bytes, content_type=content_type)
                    if settings.CLOUD_STORAGE_PUBLIC_URL:
                        return f"{settings.CLOUD_STORAGE_PUBLIC_URL.rstrip('/')}/{filename}"
                    return f"https://storage.googleapis.com/{gcs_bucket}/{filename}"
                except Exception as e:
                    logger.error(f"Google Cloud Storage upload failed: {e}")

            # 2. S3-compatible cloud storage (S3 / R2 / GCS HMAC)
            elif settings.CLOUD_STORAGE_BUCKET:
                try:
                    import boto3
                    session = boto3.session.Session()
                    s3 = session.client(
                        service_name='s3',
                        aws_access_key_id=settings.CLOUD_STORAGE_ACCESS_KEY,
                        aws_secret_access_key=settings.CLOUD_STORAGE_SECRET_KEY,
                        endpoint_url=settings.CLOUD_STORAGE_ENDPOINT or None
                    )
                    s3.put_object(
                        Bucket=settings.CLOUD_STORAGE_BUCKET,
                        Key=filename,
                        Body=file_bytes,
                        ContentType=content_type
                    )
                    if settings.CLOUD_STORAGE_PUBLIC_URL:
                        return f"{settings.CLOUD_STORAGE_PUBLIC_URL.rstrip('/')}/{filename}"
                    return f"https://{settings.CLOUD_STORAGE_BUCKET}.s3.amazonaws.com/{filename}"
                except Exception as e:
                    logger.error(f"Cloud S3 upload failed, falling back to local storage: {e}")
        
        # Local storage (Default for Localhost development)
        dest_file = self.upload_dir / filename
        with open(dest_file, "wb") as f:
            f.write(file_bytes)
        
        # Return URL relative to API base or server
        return f"{settings.API_BASE_URL.rstrip('/')}/uploads/{filename}"

    async def delete_file(self, file_url_or_name: str) -> bool:
        """Deletes a file from storage if it exists."""
        if not file_url_or_name:
            return False
        
        filename = file_url_or_name.split("/")[-1].split("?")[0]
        
        if self.mode == "cloud":
            gcs_bucket = settings.GCS_BUCKET_NAME
            if gcs_bucket:
                try:
                    import json
                    from google.cloud import storage as gcs
                    client = None
                    if settings.GCS_CREDENTIALS_JSON:
                        creds = json.loads(settings.GCS_CREDENTIALS_JSON)
                        client = gcs.Client.from_service_account_info(creds)
                    elif settings.GCS_CREDENTIALS_FILE and os.path.exists(settings.GCS_CREDENTIALS_FILE):
                        client = gcs.Client.from_service_account_json(settings.GCS_CREDENTIALS_FILE)
                    elif settings.GOOGLE_APPLICATION_CREDENTIALS and os.path.exists(settings.GOOGLE_APPLICATION_CREDENTIALS):
                        client = gcs.Client.from_service_account_json(settings.GOOGLE_APPLICATION_CREDENTIALS)
                    else:
                        client = gcs.Client(project=settings.GCS_PROJECT_ID or None)
                    bucket = client.bucket(gcs_bucket)
                    blob = bucket.blob(filename)
                    if blob.exists():
                        blob.delete()
                        logger.info(f"Deleted GCS blob: {filename}")
                        return True
                except Exception as e:
                    logger.error(f"Failed to delete GCS blob {filename}: {e}")

        # Local deletion
        local_path = self.upload_dir / filename
        if local_path.exists():
            try:
                local_path.unlink()
                logger.info(f"Deleted local file: {filename}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete local file {filename}: {e}")
        
        return False

storage_service = StorageService()
