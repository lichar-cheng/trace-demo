#!/usr/bin/env bash
# Last Edited: 2026-03-12
set -euo pipefail

cd "$(dirname "$0")/.."

required=(
  backend/app.py
  backend/models.py
  backend/schemas.py
  backend/requirements.txt
  frontend/index.html
  frontend/src/main.js
  frontend/src/services/api.js
  frontend/src/styles.css
  README.md
  docs/FULL_DELIVERY.md
  scripts/bootstrap.sh
  scripts/run_backend.sh
  scripts/run_frontend.sh
  scripts/youtube_pipeline.py
  backend/services/youtube/__init__.py
  backend/services/youtube/config.py
  backend/services/youtube/fetcher.py
  backend/services/youtube/downloader.py
  backend/services/youtube/transcriber.py
  backend/services/youtube/pipeline.py
)

missing=0
for f in "${required[@]}"; do
  if [ ! -f "$f" ]; then
    echo "[MISSING] $f"
    missing=1
  fi
done

if [ "$missing" -eq 1 ]; then
  echo "[FAIL] repository is incomplete"
  exit 1
fi

echo "[OK] repository files complete"
