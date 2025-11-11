#!/bin/bash
set -e

CONFIG_DIR=${1:-/config}

# Export Kraken API keys
export KRAKEN_API_KEY=${KRAKEN_API_KEY}
export KRAKEN_API_SECRET=${KRAKEN_API_SECRET}
export KRAKEN_API_KEY_RW=${KRAKEN_API_KEY_RW}
export KRAKEN_API_SECRET_RW=${KRAKEN_API_SECRET_RW}

# Set file paths
export TTSLO_CONFIG_FILE="${CONFIG_DIR}/config.csv"
export TTSLO_STATE_FILE="${CONFIG_DIR}/state.csv"
export TTSLO_LOG_FILE="${CONFIG_DIR}/logs.csv"

# Add uv to PATH
export PATH="/root/.local/bin:$PATH"

# Run dashboard (web UI) with host and port
uv run python dashboard.py --host 0.0.0.0 --port ${DASHBOARD_PORT:-5000}
