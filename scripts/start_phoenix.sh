#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PHOENIX_WORKING_DIR="$PWD/.phoenix"
export PHOENIX_TELEMETRY_ENABLED=false
export PHOENIX_DISABLE_AGENT_ASSISTANT=true
export PHOENIX_ENABLE_MCP_SERVER=false
export PHOENIX_ALLOW_EXTERNAL_RESOURCES=false
exec .phoenix-venv/bin/python -m phoenix.server.main serve --host 127.0.0.1 --port 6006 --grpc-port 0
