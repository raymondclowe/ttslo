#!/usr/bin/env bash
#
# setup-ttslo.sh
#
# Interactive setup wizard for TTSLO hardening and secrets provisioning on Ubuntu 24.04.
# - Prompts for Kraken API keys (read-only and read-write) and writes /etc/ttslo/ttslo.env securely
# - Ensures tc3 has an SSH authorized key before enforcing key-only SSH
# - Runs security-harden.sh to apply firewall, nginx, pam lockouts, and systemd services
# - Prints the dashboard Basic Auth credentials and access URL
#
# Safe to re-run; existing env entries can be preserved or updated.

set -euo pipefail

DEFAULT_ADMIN_USER="tc3"
ENV_DIR="/etc/ttslo"
ENV_FILE="${ENV_DIR}/ttslo.env"
REPO_DIR="/opt/ttslo"
DASHBOARD_PUBLIC_PORT=5080
APP_PORT=5000
UV_BIN="${UV_BIN:-/snap/bin/uv}"

require_root() {
  if [[ $(id -u) -ne 0 ]]; then
    echo "[ERROR] This script must be run as root (use sudo)." >&2
    exit 1
  fi
}

prompt_secret() {
  local prompt_msg="$1"
  local var_name="$2"
  local default_val="${3:-}"
  local val
  while true; do
    if [[ -n "$default_val" ]]; then
      read -r -s -p "$prompt_msg [leave blank to keep existing]: " val
      echo
      if [[ -z "$val" ]]; then
        printf -v "$var_name" '%s' "$default_val"
        return 0
      fi
    else
      read -r -s -p "$prompt_msg: " val
      echo
      if [[ -z "$val" ]]; then
        echo "Please enter a non-empty value." >&2
        continue
      fi
    fi
    printf -v "$var_name" '%s' "$val"
    return 0
  done
}

ensure_authorized_key() {
  local user="$1"
  local ak="/home/${user}/.ssh/authorized_keys"
  if [[ ! -s "$ak" ]]; then
    echo
    echo "[IMPORTANT] /home/${user}/.ssh/authorized_keys is missing or empty."
    echo "Paste a public SSH key for ${user} now (single line, e.g., ssh-ed25519 ...)."
    echo "Finish input with Ctrl+D."
    echo
    install -d -o "$user" -g "$user" -m 0700 "/home/${user}/.ssh"
    cat > "$ak"
    chown "$user":"$user" "$ak"
    chmod 600 "$ak"
  fi
}

write_env_file() {
  local ro_key="$1" ro_secret="$2" rw_key="$3" rw_secret="$4"
  install -d -m 0750 "$ENV_DIR"
  # If ttslo group exists, use it; otherwise root:root until harden script creates group
  local grp="root"
  if getent group ttslo >/dev/null 2>&1; then
    grp="ttslo"
  fi
  cat > "$ENV_FILE" <<EOF
# TTSLO environment (managed by setup-ttslo.sh)
# Kraken API keys
KRAKEN_API_KEY=${ro_key}
KRAKEN_API_SECRET=${ro_secret}
KRAKEN_API_KEY_RW=${rw_key}
KRAKEN_API_SECRET_RW=${rw_secret}

# File locations
TTSLO_CONFIG_FILE=/var/lib/ttslo/config.csv
TTSLO_STATE_FILE=/var/lib/ttslo/state.csv
TTSLO_LOG_FILE=/var/lib/ttslo/logs.csv
EOF
  chown root:"$grp" "$ENV_FILE"
  chmod 0640 "$ENV_FILE"
  echo "[OK] Wrote ${ENV_FILE} with secure permissions"
}

post_harden_fix_perms() {
  # After the harden script creates ttslo group, ensure env file group is ttslo
  if getent group ttslo >/dev/null 2>&1; then
    chgrp ttslo "$ENV_FILE" || true
    chmod 0640 "$ENV_FILE" || true
  fi
}

main() {
  require_root

  echo "TTSLO setup wizard"
  echo "- This will prompt for Kraken API keys"
  echo "- Ensure you have an SSH public key ready for ${DEFAULT_ADMIN_USER}"
  echo

  # Load existing env to offer keep-existing flow
  local EXIST_RO_KEY="" EXIST_RO_SECRET="" EXIST_RW_KEY="" EXIST_RW_SECRET=""
  if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    set -a; source "$ENV_FILE"; set +a || true
    EXIST_RO_KEY="${KRAKEN_API_KEY:-}"
    EXIST_RO_SECRET="${KRAKEN_API_SECRET:-}"
    EXIST_RW_KEY="${KRAKEN_API_KEY_RW:-}"
    EXIST_RW_SECRET="${KRAKEN_API_SECRET_RW:-}"
  fi

  local RO_KEY RO_SECRET RW_KEY RW_SECRET
  prompt_secret "Enter Kraken READ-ONLY API KEY" RO_KEY "$EXIST_RO_KEY"
  prompt_secret "Enter Kraken READ-ONLY API SECRET" RO_SECRET "$EXIST_RO_SECRET"
  prompt_secret "Enter Kraken READ-WRITE API KEY" RW_KEY "$EXIST_RW_KEY"
  prompt_secret "Enter Kraken READ-WRITE API SECRET" RW_SECRET "$EXIST_RW_SECRET"

  write_env_file "$RO_KEY" "$RO_SECRET" "$RW_KEY" "$RW_SECRET"

  # Ensure admin SSH key is present to avoid lockout
  ensure_authorized_key "$DEFAULT_ADMIN_USER"

  # Run hardening (this will clone repo, configure services, nginx, ufw, etc.)
  if [[ -x "./security-harden.sh" ]]; then
    ./security-harden.sh
  else
    echo "[ERROR] security-harden.sh not found or not executable in current directory." >&2
    exit 1
  fi

  post_harden_fix_perms

  echo
  echo "[DONE] Setup complete."
  echo "- Repo: ${REPO_DIR} (cloned and owned by root)"
  echo "- Env: ${ENV_FILE} (root:ttslo 0640)"
  echo "- Services: ttslo, ttslo-dashboard (localhost:${APP_PORT}), nginx proxy on :${DASHBOARD_PUBLIC_PORT}"
  echo "- UFW: SSH open (rate-limited), dashboard only from 192.168.0.0/24 on ${DASHBOARD_PUBLIC_PORT}"
  echo
  echo "To view service status:"
  echo "  sudo systemctl status ttslo"
  echo "  sudo systemctl status ttslo-dashboard"
  echo "  sudo journalctl -u ttslo -f"
  echo
  echo "Access the dashboard from LAN: http://<server-lan-ip>:${DASHBOARD_PUBLIC_PORT} (Basic Auth)"
}

main "$@"
