# Noah Phase 3 Final

A full-stack betting infrastructure prototype.

## Run with Docker
docker compose up -d
# API runs at: http://127.0.0.1:9010/health
# Admin UI runs at: http://127.0.0.1:8501

## Run locally
$env:PYTHONPATH = "$PWD\src"
uvicorn --app-dir src app.main:app --port 9010

## Features
- FastAPI backend with `/health` and `/composite`
- Streamlit Admin UI with kill-switch & odds composite
- Risk controls, correlation guard, and tests
- Docker Compose stack for API, Admin, Watchdog
