#!/usr/bin/env bash
set -euo pipefail

# update_prod.sh
# Push current repo, update /opt/ttslo, restart services ttslo and ttslo-dashboard.
# Usage: ./update_prod.sh ["commit message"]
# If a commit message is provided, it will be used; otherwise an automated message is created.

cd /home/tc3/ttslo || { echo "Failed to change directory to /home/tc3/ttslo"; exit 1; }

log() { printf '%s\n' "$*"; }
err() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# Determine commit message
if [ "${1:-}" = "--no-commit" ]; then
    NO_COMMIT=1
    COMMIT_MSG=""
else
    NO_COMMIT=0
    if [ -n "${1:-}" ]; then
        COMMIT_MSG="$1"
    else
        COMMIT_MSG="auto-update-$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    fi
fi

# Ensure we're in a git repo
if ! git rev-parse --git-dir >/dev/null 2>&1; then
    err "Not a git repository (run this from your project directory)."
fi

REPO_ROOT=$(git rev-parse --show-toplevel)
CUR_DIR=$(pwd)
BRANCH=$(git rev-parse --abbrev-ref HEAD)

log "Repository root: $REPO_ROOT"
log "Current directory: $CUR_DIR"
log "Current branch: $BRANCH"

# Show status
git status --porcelain=1
CHANGES=$(git status --porcelain)
if [ -n "$CHANGES" ] && [ "$NO_COMMIT" -eq 0 ]; then
    log "Staging all changes..."
    git add -A

    log "Committing changes..."
    git commit -m "$COMMIT_MSG"
elif [ -n "$CHANGES" ] && [ "$NO_COMMIT" -eq 1 ]; then
    err "Uncommitted changes present but --no-commit specified. Aborting."
else
    log "No local changes to commit."
fi

log "Pushing to origin/$BRANCH..."
git push origin "$BRANCH"

# Pull on /opt/ttslo
TARGET_DIR="/opt/ttslo"
if [ ! -d "$TARGET_DIR" ]; then
    err "$TARGET_DIR does not exist."
fi

# Verify target is a git repo
if ! sudo git -C "$TARGET_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    err "$TARGET_DIR is not a git repository (or insufficient privileges)."
fi

log "Pulling latest in $TARGET_DIR (branch: $BRANCH)..."
# Use --ff-only to avoid unexpected merges on prod; fall back to regular pull if ff-only fails
if sudo git -C "$TARGET_DIR" pull --ff-only origin "$BRANCH"; then
    log "Pulled with --ff-only."
else
    log "Fast-forward failed; attempting regular pull..."
    sudo git -C "$TARGET_DIR" pull origin "$BRANCH"
fi

# Restart services
SERVICES=(ttslo ttslo-dashboard)
for svc in "${SERVICES[@]}"; do
    log "Restarting service: $svc"
    sudo systemctl restart "$svc" || err "Failed to restart $svc"
    sleep 1
    log "Service $svc status (last lines):"
    sudo systemctl --no-pager status "$svc" -n 5 || true
done

# check that the /var/lib/config.csv has the correct 660 permissions
CONFIG_FILE="/var/lib/ttslo/config.csv"
if [ -f "$CONFIG_FILE" ]; then
    PERMS=$(stat -c "%a" "$CONFIG_FILE")
    if [ "$PERMS" != "660" ]; then
        log "Correcting permissions for $CONFIG_FILE to 660"
        sudo chmod 660 "$CONFIG_FILE" || err "Failed to set permissions on $CONFIG_FILE"
    else
        log "Permissions for $CONFIG_FILE are already correct (660)."
    fi
else
    log "$CONFIG_FILE does not exist; skipping permission check."
fi

log "Update complete."
