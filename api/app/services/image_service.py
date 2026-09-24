import io
import uuid
import logging
from typing import Tuple, Optional
from PIL import Image, ImageOps, ImageFile
from fastapi import HTTPException, status

# Allow truncated images to open if needed
ImageFile.LOAD_TRUNCATED_IMAGES = True

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB

def validate_image_upload(content_type: str, file_size: int, filename: str):
    """Validates file extension, MIME type, and size."""
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
        )

    ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS or content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image format. Allowed formats: JPG, JPEG, PNG, WebP."
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

        # Convert palette/RGBA modes to RGB for clean WebP compression
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            # Keep alpha channel for webp
            pass
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
