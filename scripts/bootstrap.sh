#!/usr/bin/env bash
# Last Edited: 2026-03-12
set -euo pipefail

cd "$(dirname "$0")/.."


source /home/ubuntu/my_env/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

echo "[OK] Python env ready"
