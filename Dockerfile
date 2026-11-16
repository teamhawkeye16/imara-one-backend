# ==============================================================================
# IMARA ONE Search — Backend Dockerfile (Fly.io Optimized)
# ==============================================================================

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Install system dependencies & libraries needed for PostgreSQL & Trafilatura
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend code, crawler module, and alembic migration config
COPY backend /app/backend
COPY crawler /app/crawler
COPY alembic.ini /app/alembic.ini

# Security: Non-root user for Fly.io container hardening
RUN addgroup --system --gid 1001 imaragroup && \
    adduser --system --uid 1001 --gid 1001 imarauser && \
    chown -R imarauser:imaragroup /app

USER imarauser

EXPOSE 8000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Start FastAPI application
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
