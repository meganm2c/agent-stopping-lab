#!/usr/bin/env bash
# Serve the saved demo; no models, Phoenix, or virtual environment needed.
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
port="${1:-8000}"
echo "Opening the saved demo at http://127.0.0.1:${port}/"
echo "Keep this terminal open. Stop with Ctrl-C."
exec python3 -m http.server "$port" --bind 127.0.0.1 --directory "$repo_root"
