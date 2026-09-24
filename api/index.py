import os
import sys
from pathlib import Path

# Add api directory and backend directory to path
api_dir = Path(__file__).resolve().parent
backend_dir = api_dir.parent / "backend"

for p in [str(api_dir), str(backend_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.main import app
