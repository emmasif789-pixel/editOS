# syntax=docker/dockerfile:1
FROM python:3.11-slim
RUN apt-get update && apt-get install -y libgl1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
# Cache mount: a retry after a network stall resumes from cached wheels instead of
# re-downloading everything from scratch. Also raise pip's timeout/retries for slow connections.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip config set global.timeout 120 && \
    pip config set global.retries 10 && \
    pip install -r requirements.txt
COPY app ./app
ENV DATA_DIR=/data
VOLUME /data
EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
