#!/usr/bin/env bash
# Last Edited: 2026-03-12
set -euo pipefail

cd "$(dirname "$0")/../frontend"
mkdir -p logs
nohup python -m http.server 4173 > logs/frontend.log 2>&1 &
