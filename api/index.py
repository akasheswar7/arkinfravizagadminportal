import os
import sys
from pathlib import Path

# Ensure api directory and backend directory are in path
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent / "backend"

for p in [str(current_dir), str(backend_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from app.main import app
except Exception:
    try:
        from .app.main import app
    except Exception as e:
        from fastapi import FastAPI
        app = FastAPI(title="ARK Infra Serverless Error Handler")
        @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
        async def fallback(path: str):
            return {"error": "Serverless import error", "detail": str(e)}
