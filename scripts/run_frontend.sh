#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../frontend"
python -m http.server 4173
