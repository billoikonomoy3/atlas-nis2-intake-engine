# Atlas — NIS2 readiness engine. Containerises the FastAPI app + deterministic engine.
#
# The deterministic core (classify/size/score/baseline) and the full test suite run
# fully OFFLINE inside this image. The extraction layer (/extract, /assess/control) is
# the only path that needs a model API key — supply it at runtime via ANTHROPIC_API_KEY;
# without it those endpoints fail closed (503), they never fabricate facts.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# Install runtime dependencies ONLY — do not `pip install .`.
#
# The engine resolves its ruleset (ruleset/nis2_v1.yaml) and the frontend
# (frontend/index.html) by a path relative to the source tree: atlas/engine/ruleset.py
# walks two parents up to the repo root and looks for ./ruleset and ./frontend. Those
# data dirs live at the repo root, NOT inside the `atlas` package, so they are never
# copied into site-packages. Installing the package (`pip install .`) relocates `atlas`
# into site-packages, where `parents[2]/ruleset` no longer exists — and ruleset.py reads
# the YAML at import time, so the import raises FileNotFoundError, uvicorn never binds a
# port, and Railway's proxy returns 502. Running straight from /app keeps the layout the
# code expects (this matches pyproject's own `pythonpath = ["."]` test contract).
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY pyproject.toml README.md server.py ./
COPY atlas ./atlas
COPY ruleset ./ruleset
COPY frontend ./frontend

EXPOSE 8000

# The container runs the API from the source tree via the single entrypoint. server.py
# binds 0.0.0.0:$PORT. Tests are not run here; CI runs them offline.
CMD ["python", "server.py"]
