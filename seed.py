"""Root seed entrypoint: ``python3 -m seed`` from the project root.

Seeds the demo workshop and exits. It never starts the HTTP server.
"""

from __future__ import annotations

from app.seed import main

if __name__ == "__main__":
    main()
