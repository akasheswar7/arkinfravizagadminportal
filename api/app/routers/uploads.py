import os
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from app.core.security import get_current_admin
from app.services.image_service import validate_image_upload, process_and_optimize_image
from app.services.storage_service import storage_service, UPLOAD_PATH

router = APIRouter(prefix="/admin", tags=["File & Photo Uploads"])
logger = logging.getLogger(__name__)

# Temporary directory for chunk assembly
CHUNK_DIR = UPLOAD_PATH / "chunks"
try:
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

@router.post("/upload-chunk")
async def upload_file_chunk(
    file: UploadFile = File(...),
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    filename: str = Form(...),
    folder: str = Form(default="general"),
    current_admin: dict = Depends(get_current_admin)
):
    """
    Handles chunked file uploads to bypass Vercel's 4.5MB payload limit.
    Splits large videos/images into small 2.5MB chunks, then reassembles them.
    Supports unlimited file sizes (16MB, 50MB, 100MB, 500MB+).
    """
    try:
        contents = await file.read()
        session_dir = CHUNK_DIR / upload_id
        session_dir.mkdir(parents=True, exist_ok=True)

        chunk_path = session_dir / f"chunk_{chunk_index}.part"
        with open(chunk_path, "wb") as f:
            f.write(contents)

        # Check how many chunks received
        received_chunks = len(list(session_dir.glob("chunk_*.part")))
        if received_chunks < total_chunks:
            return {
                "success": True,
                "completed": False,
                "progress": f"{received_chunks}/{total_chunks}",
                "message": f"Chunk {chunk_index + 1}/{total_chunks} received."
            }

        # Reassemble all chunks in numerical order
        assembled_bytes = bytearray()
        for i in range(total_chunks):
            part_file = session_dir / f"chunk_{i}.part"
            if part_file.exists():
                with open(part_file, "rb") as pf:
                    assembled_bytes.extend(pf.read())
            else:
                raise HTTPException(status_code=400, detail=f"Missing chunk {i} during file assembly.")

        # Cleanup chunk files
        try:
            for part_file in session_dir.glob("chunk_*.part"):
                part_file.unlink()
            session_dir.rmdir()
        except Exception:
            pass

        full_bytes = bytes(assembled_bytes)
        file_size = len(full_bytes)
        ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
        content_type = file.content_type or ""

        is_video = content_type.startswith("video/") or ext in {".mp4", ".mov", ".avi", ".webm", ".m4v", ".mkv"}
        is_pdf_or_doc = (
            content_type in {"application/pdf", "application/x-pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain", "text/csv"} or
            ext in {".pdf", ".doc", ".docx", ".txt", ".csv", ".xls", ".xlsx", ".zip", ".rar"} or
            (content_type and not content_type.startswith("image/") and not content_type.startswith("video/"))
        )

        if is_video:
            unique_id = uuid.uuid4().hex[:12]
            video_name = f"vid_{unique_id}{ext if ext else '.mp4'}"
            mime_type = content_type if content_type.startswith("video/") else "video/mp4"
            video_url = await storage_service.save_file(full_bytes, video_name, mime_type)

            logger.info(f"Chunked video assembled & saved: {video_name} ({file_size} bytes)")
            return {
                "success": True,
                "completed": True,
                "url": video_url,
                "video_url": video_url,
                "thumbnail_url": "images/logo.webp",
                "filename": video_name,
                "original_filename": filename,
                "size_bytes": file_size,
                "is_video": True,
                "is_pdf": False,
                "message": "Large video file uploaded and assembled successfully."
            }

        if is_pdf_or_doc:
            unique_id = uuid.uuid4().hex[:12]
            doc_name = f"doc_{unique_id}{ext if ext else '.pdf'}"
            mime_type = content_type if content_type else "application/pdf"
            doc_url = await storage_service.save_file(full_bytes, doc_name, mime_type)

            logger.info(f"Chunked PDF/document assembled & saved: {doc_name} ({file_size} bytes)")
            return {
                "success": True,
                "completed": True,
                "url": doc_url,
                "filename": doc_name,
                "original_filename": filename,
                "size_bytes": file_size,
                "is_video": False,
                "is_pdf": (ext == ".pdf" or "pdf" in content_type),
                "message": "Large document/PDF uploaded successfully."
            }

        # Image processing with safe raw-file fallback
        try:
            validate_image_upload(content_type, file_size, filename)
            max_dim = 1600 if folder == "gallery" else 800
            main_bytes, main_name, thumb_bytes, thumb_name = process_and_optimize_image(
                full_bytes,
                max_dimension=max_dim,
                quality=85,
                make_thumbnail=True
            )

            main_url = await storage_service.save_file(main_bytes, main_name, "image/webp")
            thumb_url = None
            if thumb_bytes and thumb_name:
                thumb_url = await storage_service.save_file(thumb_bytes, thumb_name, "image/webp")

            return {
                "success": True,
                "completed": True,
                "url": main_url,
                "thumbnail_url": thumb_url or main_url,
                "filename": main_name,
                "original_filename": filename,
                "size_bytes": len(main_bytes),
                "is_video": False,
                "is_pdf": False,
                "message": "Large photo uploaded and optimized successfully."
            }
        except Exception as img_err:
            logger.warning(f"Pillow image optimization skipped, saving raw image: {img_err}")
            unique_id = uuid.uuid4().hex[:12]
            raw_name = f"file_{unique_id}{ext if ext else '.bin'}"
            raw_url = await storage_service.save_file(full_bytes, raw_name, content_type or "application/octet-stream")
            return {
                "success": True,
                "completed": True,
                "url": raw_url,
                "thumbnail_url": raw_url,
                "filename": raw_name,
                "original_filename": filename,
                "size_bytes": file_size,
                "is_video": False,
                "is_pdf": ext == ".pdf",
                "message": "File uploaded successfully."
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chunk upload handler failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assemble uploaded file chunks: {str(e)}"
        )

@router.post("/upload")
async def upload_photo(
    file: UploadFile = File(...),
    folder: str = Form(default="general"),
    current_admin: dict = Depends(get_current_admin)
):
    """
    Handles standard direct upload for smaller files (<2.5MB).
    """
    try:
        contents = await file.read()
        file_size = len(contents)
        content_type = (file.content_type or "").lower()
        filename = file.filename or "file"
        ext = "." + filename.split(".")[-1].lower() if "." in filename else ""

        is_video = content_type.startswith("video/") or ext in {".mp4", ".mov", ".avi", ".webm", ".m4v", ".mkv"}
        is_pdf_or_doc = (
            content_type in {"application/pdf", "application/x-pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain", "text/csv"} or
            ext in {".pdf", ".doc", ".docx", ".txt", ".csv", ".xls", ".xlsx", ".zip", ".rar"} or
            (content_type and not content_type.startswith("image/") and not content_type.startswith("video/"))
        )

        # Handle Video File Uploads (MP4, WEBM, MOV, AVI)
        if is_video:
            unique_id = uuid.uuid4().hex[:12]
            video_name = f"vid_{unique_id}{ext if ext else '.mp4'}"
            mime_type = content_type if content_type.startswith("video/") else "video/mp4"
            video_url = await storage_service.save_file(contents, video_name, mime_type)

            logger.info(f"Video uploaded successfully: {video_name} ({file_size} bytes)")
            return {
                "success": True,
                "url": video_url,
                "video_url": video_url,
                "thumbnail_url": "images/logo.webp",
                "filename": video_name,
                "original_filename": file.filename,
                "size_bytes": file_size,
                "is_video": True,
                "is_pdf": False,
                "message": "Video file uploaded successfully."
            }

        # Handle PDF / Document Uploads
        if is_pdf_or_doc:
            unique_id = uuid.uuid4().hex[:12]
            doc_name = f"doc_{unique_id}{ext if ext else '.pdf'}"
            mime_type = content_type if content_type else "application/pdf"
            doc_url = await storage_service.save_file(contents, doc_name, mime_type)

            logger.info(f"PDF/Document uploaded successfully: {doc_name} ({file_size} bytes)")
            return {
                "success": True,
                "url": doc_url,
                "filename": doc_name,
                "original_filename": file.filename,
                "size_bytes": file_size,
                "is_video": False,
                "is_pdf": (ext == ".pdf" or "pdf" in content_type),
                "message": "PDF / Document uploaded successfully."
            }

        # Handle Image Uploads with safe raw-file fallback
        try:
            validate_image_upload(content_type, file_size, filename)
            max_dim = 1600 if folder == "gallery" else 800
            main_bytes, main_name, thumb_bytes, thumb_name = process_and_optimize_image(
                contents,
                max_dimension=max_dim,
                quality=85,
                make_thumbnail=True
            )

            main_url = await storage_service.save_file(main_bytes, main_name, "image/webp")
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
                "is_video": False,
                "is_pdf": False,
                "message": "Photo uploaded and optimized successfully."
            }
        except Exception as img_err:
            logger.warning(f"Pillow image optimization skipped, saving raw file: {img_err}")
            unique_id = uuid.uuid4().hex[:12]
            raw_name = f"file_{unique_id}{ext if ext else '.bin'}"
            raw_url = await storage_service.save_file(contents, raw_name, content_type or "application/octet-stream")
            return {
                "success": True,
                "url": raw_url,
                "thumbnail_url": raw_url,
                "filename": raw_name,
                "original_filename": file.filename,
                "size_bytes": file_size,
                "is_video": False,
                "is_pdf": ext == ".pdf",
                "message": "File uploaded successfully."
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload handler failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process and store uploaded file: {str(e)}"
        )


