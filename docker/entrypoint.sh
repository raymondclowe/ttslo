#!/bin/bash
set -e

CONFIG_DIR=${1:-/config}

# Export Kraken API keys
export KRAKEN_API_KEY=${KRAKEN_API_KEY}
export KRAKEN_API_SECRET=${KRAKEN_API_SECRET}
export KRAKEN_API_KEY_RW=${KRAKEN_API_KEY_RW}
export KRAKEN_API_SECRET_RW=${KRAKEN_API_SECRET_RW}
export TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-}

# Set file paths
export TTSLO_CONFIG_FILE="${CONFIG_DIR}/config.csv"
export TTSLO_STATE_FILE="${CONFIG_DIR}/state.csv"
export TTSLO_LOG_FILE="${CONFIG_DIR}/logs.csv"

# Set dashboard port (default to 5000 if not set)
export DASHBOARD_PORT=${DASHBOARD_PORT:-5000}

# Add uv to PATH
export PATH="/root/.local/bin:$PATH"

# Start supervisord which will manage both ttslo monitor and dashboard
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
