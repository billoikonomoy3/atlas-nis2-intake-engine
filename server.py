"""Process entrypoint for Atlas — `python server.py`.

Railway (and any platform that launches the app with `python server.py`) starts the
service through this file. It boots the FastAPI app bound to 0.0.0.0:$PORT so the
platform's edge proxy can reach the container. Binding to anything other than 0.0.0.0,
or to a port other than the one in $PORT, is exactly what makes that proxy return 502.

This is the single launch path: the Dockerfile CMD and the Procfile both invoke
`python server.py`, so there is one entrypoint to keep correct rather than three.
"""

from __future__ import annotations

import os

import uvicorn

# Import the app from the source tree (atlas/ lives next to this file at the repo root,
# which is /app in the container). Importing here — rather than passing uvicorn the
# "atlas.api.main:app" import string — guarantees the import uses this file's sys.path.
from atlas.api.main import app


def main() -> None:
    # Railway injects PORT at runtime; 8000 is a sane default for a local `python server.py`.
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
