#!/bin/sh
set -euo pipefail

UVICORN_WORKERS=${UVICORN_WORKERS:-4}
UVICORN_HOST=${UVICORN_HOST:-0.0.0.0}
UVICORN_PORT=${UVICORN_PORT:-8000}

start_server() {
  exec uvicorn app.main:app \
    --host "${UVICORN_HOST}" \
    --port "${UVICORN_PORT}" \
    --workers "${UVICORN_WORKERS}" \
    --proxy-headers
}

start_server &
SERVER_PID=$!

cleanup() {
  kill -TERM "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID"
}

trap cleanup INT TERM

for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${UVICORN_PORT}/health" >/dev/null; then
    curl -fsS -X POST "http://127.0.0.1:${UVICORN_PORT}/warmup" || true
    break
  fi
  sleep 1
done

wait "$SERVER_PID"
