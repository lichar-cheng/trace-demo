#!/usr/bin/env bash
# Last Edited: 2026-03-12
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

echo "[OK] Python env ready"
