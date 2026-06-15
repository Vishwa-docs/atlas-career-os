# syntax=docker/dockerfile:1
# Multi-stage build. The same image runs both the API (uvicorn) and the ARQ
# worker — the start command differs (see docker-compose / Render services).
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Build deps for asyncpg/argon2 etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install ".[dev]"

COPY . .

EXPOSE 8000

# Default: serve the API. Bind to $PORT when the host provides one (Render,
# Cloud Run, etc.); default to 8000 locally (docker-compose maps 8000:8000).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
