# syntax=docker/dockerfile:1
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 9010 8501
ENV MODEL_PATH=artifacts/model.joblib
ENV PYTHONUNBUFFERED=1

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS http://127.0.0.1:9010/health || exit 1

CMD ["python","-m","uvicorn","src.serve.api:app","--host","0.0.0.0","--port","9010"]
