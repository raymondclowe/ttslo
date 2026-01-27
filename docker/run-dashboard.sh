#!/bin/bash
# Wrapper script to inject DASHBOARD_PORT into command

# Validate DASHBOARD_PORT is a number between 1-65535
PORT=${DASHBOARD_PORT:-5000}
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    echo "ERROR: Invalid DASHBOARD_PORT '$PORT'. Must be a number between 1 and 65535." >&2
    exit 1
fi

exec /root/.local/bin/uv run python dashboard.py --host 0.0.0.0 --port "$PORT"
