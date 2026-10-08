import io
import uuid
import logging
from typing import Tuple, Optional
from PIL import Image, ImageOps, ImageFile
from fastapi import HTTPException, status

# Allow truncated images to open if needed
ImageFile.LOAD_TRUNCATED_IMAGES = True

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".jfif", ".pjpeg", ".pjp",
    ".avif", ".heic", ".heif", ".bmp", ".tiff", ".tif", ".pdf",
    ".doc", ".docx", ".txt", ".csv", ".xls", ".xlsx", ".zip", ".rar",
    ".mp4", ".mov", ".avi", ".webm", ".m4v", ".mkv"
}
ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/jpg", "image/pjpeg", "image/jfif", "image/pjp",
    "image/png", "image/x-png", "image/webp", "image/heic", "image/heif",
    "image/heic-sequence", "image/heif-sequence", "image/avif", "image/bmp",
    "image/x-ms-bmp", "image/tiff", "application/octet-stream", "application/pdf",
    "application/x-pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain", "text/csv", "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/zip", "application/x-rar-compressed"
}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB (virtually unlimited)

def validate_image_upload(content_type: str, file_size: int, filename: str):
    """Validates file extension, MIME type, and size."""
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum allowed size is 5GB."
        )

    norm_type = (content_type or "").lower().split(";")[0].strip()
    ext = "." + filename.split(".")[-1].lower() if "." in filename else ""

    is_valid_ext = ext in ALLOWED_EXTENSIONS or bool(ext)
    is_valid_mime = norm_type in ALLOWED_MIME_TYPES or norm_type.startswith("image/") or norm_type.startswith("application/") or norm_type.startswith("video/") or norm_type.startswith("text/")

    if not is_valid_ext and not is_valid_mime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Allowed formats: PDF, JPG, JPEG, PNG, WebP, AVIF, HEIC, JFIF, DOC, DOCX, TXT."
        )

def process_and_optimize_image(
    file_bytes: bytes,
    max_dimension: int = 1600,
    quality: int = 85,
    make_thumbnail: bool = True
) -> Tuple[bytes, str, Optional[bytes], Optional[str]]:
    """
    Safely opens an image using Pillow, auto-rotates by EXIF,
    resizes if larger than max_dimension, converts to WebP,
    and optionally produces a compact 320x320 thumbnail.
    
    Returns: (main_image_bytes, main_filename, thumb_bytes, thumb_filename)
    """
    try:
        img = Image.open(io.BytesIO(file_bytes))
        
        # Handle EXIF rotation (e.g. mobile photo orientations)
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        # Convert palette/RGBA modes cleanly for WebP compression
        if img.mode in ("RGBA", "LA"):
            pass
        elif img.mode == "P" and "transparency" in img.info:
            img = img.convert("RGBA")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Resize main image if larger than max_dimension while preserving aspect ratio
        w, h = img.size
        if max(w, h) > max_dimension:
            scale = max_dimension / float(max(w, h))
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Save main image as WebP
        main_buffer = io.BytesIO()
        img.save(main_buffer, format="WEBP", quality=quality, method=6)
        main_bytes = main_buffer.getvalue()

        unique_id = uuid.uuid4().hex[:12]
        main_filename = f"img_{unique_id}.webp"

        # Generate thumbnail if requested
        thumb_bytes = None
        thumb_filename = None
        if make_thumbnail:
            thumb_img = img.copy()
            thumb_img.thumbnail((320, 320), Image.Resampling.LANCZOS)
            thumb_buffer = io.BytesIO()
            thumb_img.save(thumb_buffer, format="WEBP", quality=80)
            thumb_bytes = thumb_buffer.getvalue()
            thumb_filename = f"thumb_{unique_id}.webp"

        return main_bytes, main_filename, thumb_bytes, thumb_filename

    except Exception as e:
        logger.error(f"Image processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid or readable image."
        )
