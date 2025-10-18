# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (curl for healthcheck, build essentials if needed)
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY src ./src
COPY ui ./ui
COPY config.yml ./config.yml

# Defaults (can be overridden by compose)
ENV UVICORN_APP="app.main:app" \
    BIND_HOST="0.0.0.0" \
    BIND_PORT="9010"

EXPOSE 9010 8501

# Default command is API; compose will override for admin + watchdog
CMD ["python","-m","uvicorn","--app-dir","src","app.main:app","--host","0.0.0.0","--port","9010","--log-level","info"]
