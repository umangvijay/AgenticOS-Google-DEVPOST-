# Cloud Run API image (also used as Dockerfile.api).
# Designed to succeed on Cloud Build: no Playwright browsers, pip with deps,
# no frontend/terraform in the context.

FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi8 \
    shared-mime-info \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY main.py ./main.py

ENV PYTHONPATH=/app \
    PORT=8080 \
    APP_ENV=production \
    STORAGE_BACKEND=sqlite \
    PYTHONUNBUFFERED=1

EXPOSE 8080

# Cloud Run sets PORT. Do not bake .env into this image.
CMD ["sh", "-c", "exec uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
