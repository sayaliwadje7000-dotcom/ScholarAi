FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    TESSERACT_CMD=/usr/bin/tesseract \
    DOCUMENT_STORAGE_ROOT=/app/storage

WORKDIR /app

# Install system dependencies required for OCR.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install production dependencies separately for better layer caching.
COPY requirements-prod.txt .

RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements-prod.txt

# Copy backend application and migration files.
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

# Create non-root user and persistent storage directories.
RUN groupadd --system scholarai \
    && useradd --system --gid scholarai --home-dir /app scholarai \
    && mkdir -p /app/storage/documents \
                /app/storage/processed \
                /app/storage/temporary \
    && chown -R scholarai:scholarai /app

USER scholarai

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
