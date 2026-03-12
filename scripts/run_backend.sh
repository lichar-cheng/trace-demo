#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate || {
  echo "[ERR] .venv not found, run: bash scripts/bootstrap.sh"
  exit 1
}

python backend/app.txt
