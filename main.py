"""Root entrypoint.

Two supported launch commands resolve to the same ASGI app:

    uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
    uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
    python3 main.py
"""

from __future__ import annotations

import os

from app.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        log_level="info",
    )
