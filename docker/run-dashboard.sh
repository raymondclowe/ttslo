#!/bin/bash
# Wrapper script to inject DASHBOARD_PORT into command
exec /root/.local/bin/uv run python dashboard.py --host 0.0.0.0 --port ${DASHBOARD_PORT:-5000}
