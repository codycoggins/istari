FROM python:3.12-slim AS base

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (cache layer)
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source
COPY src/ src/
COPY alembic.ini .
COPY migrations/ migrations/

# Re-install with source (picks up the package)
RUN pip install --no-cache-dir .

# Default: run API (overridden per service in docker-compose.yml)
CMD ["uvicorn", "istari.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
