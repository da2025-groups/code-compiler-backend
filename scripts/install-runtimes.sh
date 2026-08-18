#!/usr/bin/env bash
# First-time Piston runtime setup. Run after: docker-compose up -d
set -euo pipefail

PISTON_URL="${PISTON_URL:-http://localhost:2000}"
LANGUAGES=("python" "javascript" "java" "c++" "c" "go" "rust")

echo "Waiting for Piston at ${PISTON_URL}..."
until curl -sf "${PISTON_URL}/api/v2/runtimes" > /dev/null 2>&1; do
  sleep 3
done
echo "Piston ready. Installing ${#LANGUAGES[@]} runtimes..."

for lang in "${LANGUAGES[@]}"; do
  echo "  -> ${lang}"
  curl -sf -X POST "${PISTON_URL}/api/v2/packages" \
    -H "Content-Type: application/json" \
    -d "{\"language\": \"${lang}\", \"version\": \"*\"}" > /dev/null || \
    echo "  WARNING: ${lang} may have failed (already installed?)"
done

echo "Done. Installed runtimes:"
curl -sf "${PISTON_URL}/api/v2/runtimes" | python3 -c \
  "import sys,json; [print(f'  {r[\"language\"]} {r[\"version\"]}') for r in json.load(sys.stdin)]"
