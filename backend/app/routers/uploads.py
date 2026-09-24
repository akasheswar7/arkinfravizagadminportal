import logging
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from app.core.security import get_current_admin
from app.services.image_service import validate_image_upload, process_and_optimize_image
from app.services.storage_service import storage_service

router = APIRouter(prefix="/admin", tags=["File & Photo Uploads"])
logger = logging.getLogger(__name__)

@router.post("/upload")
async def upload_photo(
    file: UploadFile = File(...),
    folder: str = Form(default="general"),
    current_admin: dict = Depends(get_current_admin)
):
    """
    Handles robust photo upload with Pillow:
    1. Validates extension, MIME type, file size
    2. Auto-rotates orientation by EXIF
    3. Resizes & compresses to modern WebP
    4. Generates a compact thumbnail
    5. Saves to storage and returns direct URLs
    """
    try:
        contents = await file.read()
        file_size = len(contents)
        
        # Validation
        validate_image_upload(file.content_type, file_size, file.filename)

        # Process and optimize image
        max_dim = 1600 if folder == "gallery" else 800
        main_bytes, main_name, thumb_bytes, thumb_name = process_and_optimize_image(
            contents,
            max_dimension=max_dim,
            quality=85,
            make_thumbnail=True
        )

        # Save main WebP image
        main_url = await storage_service.save_file(main_bytes, main_name, "image/webp")

        # Save thumbnail WebP
        thumb_url = None
        if thumb_bytes and thumb_name:
            thumb_url = await storage_service.save_file(thumb_bytes, thumb_name, "image/webp")

        logger.info(f"Photo uploaded successfully: {main_name} ({file_size} -> {len(main_bytes)} bytes)")

        return {
            "success": True,
            "url": main_url,
            "thumbnail_url": thumb_url or main_url,
            "filename": main_name,
            "original_filename": file.filename,
            "size_bytes": len(main_bytes),
            "message": "Photo uploaded and optimized successfully."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload handler failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process and store uploaded image: {str(e)}"
        )
