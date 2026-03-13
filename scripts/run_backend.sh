#!/usr/bin/env bash
# Last Edited: 2026-03-12
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p logs
source /home/ubuntu/my_env/bin/activate || {
  echo "[ERR] myenv not found, run: bash scripts/bootstrap.sh"
  exit 1
}
nohup python backend/app.py > logs/backend.log 2>&1 &
