#!/usr/bin/env bash
#
# remove-security-harden.s
#
# Purpose: Revert the changes made by security-harden.sh on Ubuntu 24.04
# - Restore sshd_config, PAM faillock, UFW, nginx site, and disable the systemd service
# - Remove users/dirs only if created by the hardening script (conservative)
# - Uses backups with .bak.ttslo* when present; otherwise removes the inserted blocks
#
# Requires sudo/root. Safe to run multiple times.

set -euo pipefail

ADMIN_USER="tc3"
DEPLOY_PATH="/opt/ttslo"
DATA_PATH="/var/lib/ttslo"
ENV_PATH="/etc/ttslo/ttslo.env"
SERVICE_USER="ttslo"
SERVICE_GROUP="ttslo"

require_root() {
  if [[ $(id -u) -ne 0 ]]; then
    echo "[ERROR] This script must be run as root (use sudo)." >&2
    exit 1
  fi
}

restore_latest_backup() {
  local file="$1"
  local backup
  backup=$(ls -1t ${file}.bak.ttslo.* 2>/dev/null | head -n1 || true)
  if [[ -n "$backup" ]]; then
    cp -a "$backup" "$file"
    echo "[OK] Restored backup for $file from $backup"
    return 0
  fi
  return 1
}

remove_block() {
  local file="$1"
  local start_marker="$2"
  local end_marker="$3"
  [[ -f "$file" ]] || return 0
  awk -v start="$start_marker" -v end="$end_marker" '
    $0 ~ start {skip=1; next}
    $0 ~ end && skip==1 {skip=0; next}
    skip!=1 {print}
  ' "$file" >"${file}.tmp" && mv "${file}.tmp" "$file"
}

revert_sshd() {
  echo "[STEP] Reverting sshd changes (keeping key auth working)"
  local sshd="/etc/ssh/sshd_config"
  if ! restore_latest_backup "$sshd"; then
    remove_block "$sshd" "# BEGIN ttslo-hardening" "# END ttslo-hardening"
  fi
  systemctl reload ssh || true
  echo "[OK] sshd reverted."
}

revert_pam() {
  echo "[STEP] Reverting PAM faillock changes"
  local sshd_pam="/etc/pam.d/sshd"
  local sudo_pam="/etc/pam.d/sudo"

  if ! restore_latest_backup "$sshd_pam"; then
    remove_block "$sshd_pam" "# ttslo-hardening pam_faillock start" "# ttslo-hardening pam_faillock end"
  fi
  if ! restore_latest_backup "$sudo_pam"; then
    remove_block "$sudo_pam" "# ttslo-hardening pam_faillock start" "# ttslo-hardening pam_faillock end"
  fi
  echo "[OK] PAM reverted."
}

revert_ufw() {
  echo "[STEP] Reverting UFW rules (keeping UFW enabled)"
  # We won’t disable UFW; we’ll just remove typical rules we added.
  # Dashboard rules likely referenced nginx public port; manual review recommended.
  # Using numbered rule deletion is tricky; instead we reset to defaults if safe.
  # Conservative approach: keep UFW as-is. Uncomment below if you want to reset.
  # ufw --force reset
  echo "[INFO] UFW left unchanged (manual review recommended if needed)."
}

revert_nginx() {
  echo "[STEP] Removing nginx dashboard site"
  local site_avail="/etc/nginx/sites-available/ttslo-dashboard.conf"
  local site_enabled="/etc/nginx/sites-enabled/ttslo-dashboard.conf"
  rm -f "$site_enabled" || true
  rm -f "$site_avail" || true
  rm -f "/etc/nginx/.htpasswd-ttslo" || true
  nginx -t && systemctl reload nginx || true
  echo "[OK] Nginx dashboard site removed."
}

revert_systemd() {
  echo "[STEP] Disabling TTSLO systemd service"
  systemctl disable --now ttslo || true
  systemctl disable --now ttslo-dashboard || true
  rm -f /etc/systemd/system/ttslo.service || true
  rm -f /etc/systemd/system/ttslo-dashboard.service || true
  systemctl daemon-reload || true
  echo "[OK] Service disabled and unit removed."

  # Keep data and deploy by default; comment out to remove
  # rm -rf "$DEPLOY_PATH" || true
  # rm -rf "$DATA_PATH" || true
  # Optionally remove service user if it exists and has no home content
  # if id -u "$SERVICE_USER" >/dev/null 2>&1; then
  #   deluser --system "$SERVICE_USER" || true
  # fi
}

main() {
  require_root
  revert_sshd
  revert_pam
  revert_ufw
  revert_nginx
  revert_systemd

  echo
  echo "[DONE] Reverted hardening changes (conservative). Review SSH/UFW settings before exposing the host."
}

main "$@"
