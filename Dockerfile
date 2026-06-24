# Atlas — NIS2 readiness engine. Containerises the FastAPI app + deterministic engine.
#
# The deterministic core (classify/size/score/baseline) and the full test suite run
# fully OFFLINE inside this image. The extraction layer (/extract, /assess/control) is
# the only path that needs a model API key — supply it at runtime via ANTHROPIC_API_KEY;
# without it those endpoints fail closed (503), they never fabricate facts.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

COPY pyproject.toml README.md ./
COPY atlas ./atlas
COPY ruleset ./ruleset
COPY frontend ./frontend

RUN pip install --upgrade pip && pip install .

EXPOSE 8000

# The container runs the API. Tests are not run here; CI runs them offline.
CMD ["sh", "-c", "uvicorn atlas.api.main:app --host 0.0.0.0 --port ${PORT}"]
