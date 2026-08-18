#!/usr/bin/env bash
# ==============================================================================
# EOJ Judge Server - Fast Sandboxed Docker Runner (Zero Downloads)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER_NAME="eoj-judge-server"
PORT=5055

echo "🛑 Removing previous judge container if running..."
sudo docker rm -f "${CONTAINER_NAME}" 2>/dev/null || true

echo "🚀 Starting sandboxed EOJ Judge Server on port ${PORT}..."
sudo docker run -d \
  --name "${CONTAINER_NAME}" \
  -p "${PORT}:${PORT}" \
  -v /usr:/usr:ro \
  -v /lib:/lib:ro \
  -v /lib64:/lib64:ro \
  -v /opt:/opt:ro \
  -v "${SCRIPT_DIR}:/app" \
  -w /app \
  --tmpfs /tmp:rw,exec,nosuid,size=512m \
  --restart always \
  ubuntu:24.04 \
  python3 server.py

echo "⏳ Waiting for judge server to initialize..."
sleep 2

if curl -s "http://127.0.0.1:${PORT}/api/languages" > /dev/null 2>&1; then
  echo "✅ Sandboxed EOJ Judge Server is ONLINE at http://127.0.0.1:${PORT}"
  curl -s "http://127.0.0.1:${PORT}/api/languages" | python3 -m json.tool | head -n 30 || true
else
  echo "⚠️ Container started. Checking logs:"
  sudo docker logs "${CONTAINER_NAME}"
fi
