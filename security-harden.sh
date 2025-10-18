#!/usr/bin/env bash
#
# security-harden.sh
#
# Purpose: Apply a practical hardening baseline on Ubuntu 24.04 for running TTSLO
# - SSH: key-only over SSH (passwords still allowed at console login)
# - PAM: temporary lockouts after repeated failed attempts (ssh and sudo)
# - UFW: default deny incoming, allow outgoing; allow SSH; allow dashboard from LAN only
# - Nginx: reverse proxy to local Flask dashboard with Basic Auth
# - Systemd: run TTSLO as locked-down service user with sandboxing
#
# Notes
# - Safe to run multiple times (idempotent where possible)
# - Creates backups of critical config files with .bak.ttslo timestamps
# - Requires sudo/root
#
# Recovery
# - Console login for user tc3 with password remains functional (only SSH is key-only)
# - If you get locked out by PAM faillock, use console and run:
#     pam_faillock --user <your-admin-user> --reset
# - To revert all changes, run ./remove-security-harden.sh

set -euo pipefail

#############################
# Configuration (edit here) #
#############################

# IMPORTANT: Change ADMIN_USER to match your actual admin username
# Admin user that will SSH to the box
ADMIN_USER="tc3"

# Dashboard configuration
# App (Flask) listens locally on this port
APP_PORT="5000"
# Nginx will listen on this port for LAN clients and proxy to APP_PORT
DASHBOARD_PUBLIC_PORT="5080"
DASHBOARD_LISTEN_IP="0.0.0.0"       # nginx listen address for LAN
DASHBOARD_BASIC_AUTH_USER="dashboard"
# If empty, a strong random password will be generated and printed
DASHBOARD_BASIC_AUTH_PASSWORD=""

# UFW: allow SSH from anywhere (rate-limited) and dashboard only from private subnets
# LAN CIDR(s) allowed to reach nginx proxy for the dashboard
# Assuming your LAN is 192.168.0.0/24; change if needed
ALLOW_DASHBOARD_CIDRS=(
  "192.168.0.0/24"
)

# Optional: install and enable fail2ban for sshd (complements PAM lockouts)
ENABLE_FAIL2BAN="false"

# Application deployment
DEPLOY_PATH="/opt/ttslo"            # where repo code will live (read-only)
DATA_PATH="/var/lib/ttslo"          # state/logs owned by service user
ENV_PATH="/etc/ttslo/ttslo.env"     # env file with Kraken keys (can be empty)
SERVICE_USER="ttslo"
SERVICE_GROUP="ttslo"

# How to run the service
USE_UV="true"                        # if false, use venv python instead
UV_BIN="/usr/bin/uv"
VENV_PY="${DEPLOY_PATH}/.venv/bin/python"


#################################
# Helpers and environment checks #
#################################

require_root() {
  if [[ $(id -u) -ne 0 ]]; then
    echo "[ERROR] This script must be run as root (use sudo)." >&2
    exit 1
  fi
}

backup_file() {
  local file="$1"
  if [[ -f "$file" ]]; then
    local ts
    ts=$(date +%Y%m%d_%H%M%S)
    cp -a "$file" "${file}.bak.ttslo.${ts}"
    echo "[INFO] Backup: ${file} -> ${file}.bak.ttslo.${ts}"
  fi
}

file_has_block() {
  local file="$1"
  local start_marker="$2"
  local end_marker="$3"
  awk "/${start_marker}/ {f=1} /${end_marker}/ {if(f){print; exit 0}} END{exit 1}" "$file" >/dev/null 2>&1
}

insert_or_replace_block() {
  local file="$1"; shift
  local start_marker="$1"; shift
  local end_marker="$1"; shift
  local content="$*"

  mkdir -p "$(dirname "$file")"
  touch "$file"

  if file_has_block "$file" "$start_marker" "$end_marker"; then
    # Replace existing block
    awk -v start="$start_marker" -v end="$end_marker" -v repl="$content" '
      BEGIN{printed=0}
      $0 ~ start {print; print repl; skip=1; next}
      $0 ~ end && skip==1 {print; skip=0; next}
      skip!=1 {print}
    ' "$file" >"${file}.tmp"
    mv "${file}.tmp" "$file"
  else
    # Append new block
    {
      echo "$start_marker"
      echo "$content"
      echo "$end_marker"
    } >>"$file"
  fi
}

ensure_package() {
  local pkg="$1"
  if ! dpkg -s "$pkg" >/dev/null 2>&1; then
    apt-get update -y
    DEBIAN_FRONTEND=noninteractive apt-get install -y "$pkg"
  fi
}

rand_password() {
  # 24 chars base64 without special characters
  openssl rand -base64 32 | tr -d '\n' | cut -c1-24
}

########################################
# 1) SSH: key-only over SSH (console ok) #
########################################
configure_sshd() {
  echo "[STEP] Configuring sshd for key-only auth over SSH (console unaffected)"

  # Safety: ensure the admin user has an authorized_keys file with at least one key
  local auth_keys="/home/${ADMIN_USER}/.ssh/authorized_keys"
  if [[ ! -s "$auth_keys" ]]; then
    echo "[ERROR] ${auth_keys} is missing or empty. To avoid lockout, add a public key first." >&2
    exit 1
  fi
  
  # Validate that authorized_keys contains at least one valid SSH public key
  if ! grep -qE '^(ssh-rsa|ssh-ed25519|ecdsa-sha2-nistp256|ecdsa-sha2-nistp384|ecdsa-sha2-nistp521|sk-ssh-ed25519@openssh.com|sk-ecdsa-sha2-nistp256@openssh.com) ' "$auth_keys"; then
    echo "[ERROR] ${auth_keys} does not contain any valid SSH public keys. To avoid lockout, add a valid key first." >&2
    echo "[ERROR] Supported key types: ssh-rsa, ssh-ed25519, ecdsa-*, sk-ssh-ed25519@openssh.com, sk-ecdsa-*" >&2
    exit 1
  fi
  
  chown ${ADMIN_USER}:${ADMIN_USER} "$auth_keys" || true
  chmod 600 "$auth_keys" || true

  local sshd="/etc/ssh/sshd_config"
  backup_file "$sshd"

  local start="# BEGIN ttslo-hardening"
  local end="# END ttslo-hardening"
  local block
  read -r -d '' block <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
MaxAuthTries 3
UsePAM yes
# Optional: restrict users
# AllowUsers tc3
EOF

  insert_or_replace_block "$sshd" "$start" "$end" "$block"
  systemctl reload ssh
  echo "[OK] sshd reloaded. Existing SSH sessions continue; new sessions require keys."
}

#######################################
# 2) PAM faillock for ssh and sudo     #
#######################################
configure_pam_faillock() {
  echo "[STEP] Enabling PAM faillock for SSH and sudo only (deny=5, unlock_time=900s)"
  ensure_package libpam-modules

  local sshd_pam="/etc/pam.d/sshd"
  local sudo_pam="/etc/pam.d/sudo"

  backup_file "$sshd_pam"
  backup_file "$sudo_pam"

  local start="# ttslo-hardening pam_faillock start"
  local end="# ttslo-hardening pam_faillock end"
  local block_sshd
  read -r -d '' block_sshd <<'EOF'
auth required pam_faillock.so preauth silent deny=5 unlock_time=900
auth [success=1 default=bad] pam_unix.so
auth [default=die] pam_faillock.so authfail deny=5 unlock_time=900
auth sufficient pam_faillock.so authsucc
EOF
  insert_or_replace_block "$sshd_pam" "$start" "$end" "$block_sshd"

  local block_sudo
  read -r -d '' block_sudo <<'EOF'
auth required pam_faillock.so preauth silent deny=5 unlock_time=900
auth [success=1 default=bad] pam_unix.so
auth [default=die] pam_faillock.so authfail deny=5 unlock_time=900
auth sufficient pam_faillock.so authsucc
EOF
  insert_or_replace_block "$sudo_pam" "$start" "$end" "$block_sudo"

  echo "[OK] PAM faillock configured for sshd and sudo. Use 'pam_faillock --user ${ADMIN_USER} --reset' if needed."
}

##############################
# 3) UFW baseline + dashboard #
##############################
configure_ufw() {
  echo "[STEP] Configuring UFW (deny incoming, allow outgoing, allow SSH, LAN-only dashboard)"
  ensure_package ufw

  # Ensure defaults
  ufw --force default deny incoming || true
  ufw --force default allow outgoing || true

  # SSH allow + rate limit
  ufw allow OpenSSH || true
  ufw limit OpenSSH || true

  # Dashboard from RFC1918 only (public port served by nginx)
  for cidr in "${ALLOW_DASHBOARD_CIDRS[@]}"; do
    ufw allow from "$cidr" to any port "$DASHBOARD_PUBLIC_PORT" proto tcp || true
  done

  # Enable UFW (non-interactive)
  ufw --force enable || true
  echo "[OK] UFW configured."
}

############################################
# 4) Nginx reverse proxy with Basic Auth   #
############################################
configure_nginx_dashboard() {
  echo "[STEP] Installing nginx reverse proxy with Basic Auth for dashboard"
  ensure_package nginx
  ensure_package apache2-utils   # for htpasswd

  mkdir -p /etc/nginx
  local htpasswd_file="/etc/nginx/.htpasswd-ttslo"

  if [[ -z "$DASHBOARD_BASIC_AUTH_PASSWORD" ]]; then
    DASHBOARD_BASIC_AUTH_PASSWORD=$(rand_password)
    echo "[INFO] Generated dashboard password for user '${DASHBOARD_BASIC_AUTH_USER}': ${DASHBOARD_BASIC_AUTH_PASSWORD}"
    echo "[SECURITY] Save this password now! It will not be displayed again."
  fi

  # Create/update htpasswd entry idempotently
  if grep -q "^${DASHBOARD_BASIC_AUTH_USER}:" "$htpasswd_file" 2>/dev/null; then
    htpasswd -bB "$htpasswd_file" "$DASHBOARD_BASIC_AUTH_USER" "$DASHBOARD_BASIC_AUTH_PASSWORD" >/dev/null
  else
    htpasswd -bBc "$htpasswd_file" "$DASHBOARD_BASIC_AUTH_USER" "$DASHBOARD_BASIC_AUTH_PASSWORD" >/dev/null
  fi
  chmod 640 "$htpasswd_file"
  chown root:www-data "$htpasswd_file" || true

  local site_avail="/etc/nginx/sites-available/ttslo-dashboard.conf"
  local site_enabled="/etc/nginx/sites-enabled/ttslo-dashboard.conf"

  backup_file "$site_avail"

  cat > "$site_avail" <<EOF
# ttslo dashboard reverse proxy (managed by security-harden.sh)
server {
    listen ${DASHBOARD_LISTEN_IP}:${DASHBOARD_PUBLIC_PORT};
    server_name _;

    access_log /var/log/nginx/ttslo_dashboard_access.log;
    error_log  /var/log/nginx/ttslo_dashboard_error.log;

    location / {
        auth_basic "TTSLO Dashboard";
        auth_basic_user_file ${htpasswd_file};

        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_buffering off;
    }
}
EOF

  ln -sf "$site_avail" "$site_enabled"
  # Disable default site if it exists to avoid port conflicts
  if [[ -e /etc/nginx/sites-enabled/default ]]; then
    rm -f /etc/nginx/sites-enabled/default
  fi

  nginx -t
  systemctl reload nginx
  echo "[OK] Nginx configured for dashboard with Basic Auth (restricted via UFW to LAN)."
}

############################################
# 5) Systemd service, user, and filesystem #
############################################
configure_systemd_service() {
  echo "[STEP] Setting up TTSLO systemd service with sandboxing"

  # Create service user/group if needed
  if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
    adduser --system --home "$DATA_PATH" --group --shell /usr/sbin/nologin "$SERVICE_USER"
  fi

  install -d -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0750 "$DATA_PATH"
  install -d -o root -g root -m 0755 "$DEPLOY_PATH"

  # Deploy production code via git clone (read-only for root)
  ensure_package git
  if [[ ! -d "$DEPLOY_PATH/.git" ]]; then
    echo "[INFO] Cloning production repo into $DEPLOY_PATH"
    git clone https://github.com/raymondclowe/ttslo "$DEPLOY_PATH"
    chown -R root:root "$DEPLOY_PATH"
    chmod -R a=rX,u+w "$DEPLOY_PATH"
  else
    echo "[INFO] Repo already present at $DEPLOY_PATH; leaving code unchanged"
  fi

  # Environment file (root:group 0640)
  install -d -o root -g "$SERVICE_GROUP" -m 0750 "$(dirname "$ENV_PATH")"
  if [[ -f "$DEPLOY_PATH/deploy/systemd/ttslo.env.example" && ! -f "$ENV_PATH" ]]; then
    install -o root -g "$SERVICE_GROUP" -m 0640 "$DEPLOY_PATH/deploy/systemd/ttslo.env.example" "$ENV_PATH"
  fi

  # Install service unit
  local unit_src="$DEPLOY_PATH/deploy/systemd/ttslo.service"
  local unit_dst="/etc/systemd/system/ttslo.service"
  if [[ -f "$unit_src" ]]; then
    install -m 0644 "$unit_src" "$unit_dst"
  else
    echo "[WARN] Service unit not found at $unit_src; skipping"
    return 0
  fi

  # If USE_UV=false, update ExecStart to use venv python
  if [[ "$USE_UV" != "true" ]]; then
    if [[ ! -x "$VENV_PY" ]]; then
      echo "[INFO] Creating venv and installing deps for service"
      ensure_package python3-venv
      python3 -m venv "${DEPLOY_PATH}/.venv"
      "${DEPLOY_PATH}/.venv/bin/pip" install -U pip
      # Try to install dependencies from uv/pyproject fallback
      if [[ -f "$DEPLOY_PATH/pyproject.toml" ]]; then
        "${DEPLOY_PATH}/.venv/bin/pip" install -e "$DEPLOY_PATH"
      fi
    fi
    sed -i "s|^ExecStart=.*|ExecStart=${VENV_PY} ${DEPLOY_PATH}/ttslo.py --interval 60|" "$unit_dst"
  else
    # Ensure uv is present or warn
    if [[ ! -x "$UV_BIN" ]]; then
      echo "[WARN] $UV_BIN not found; consider setting USE_UV=false to use a venv." >&2
    fi
  fi

  systemctl daemon-reload
  systemctl enable --now ttslo || true
  systemctl status --no-pager --lines=5 ttslo || true
  echo "[OK] TTSLO service installed and started."
}

############################################
# 5b) Dashboard systemd service (localhost) #
############################################
configure_dashboard_service() {
  echo "[STEP] Setting up TTSLO Dashboard systemd service (binds to 127.0.0.1:${APP_PORT})"

  local unit_src="$DEPLOY_PATH/deploy/systemd/ttslo-dashboard.service"
  local unit_dst="/etc/systemd/system/ttslo-dashboard.service"

  if [[ ! -f "$unit_src" ]]; then
    echo "[WARN] Dashboard unit template not found at $unit_src; creating from template in script"
    cat > "$unit_dst" <<EOF
[Unit]
Description=TTSLO Dashboard (Flask) - localhost only
After=network-online.target
Wants=network-online.target

[Service]
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${DEPLOY_PATH}
EnvironmentFile=${ENV_PATH}
Environment=PYTHONUNBUFFERED=1
Environment=UV_SYSTEM_PYTHON=1
ExecStart=${UV_BIN} run python dashboard.py --host 127.0.0.1 --port ${APP_PORT}
Restart=on-failure
RestartSec=5s

NoNewPrivileges=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectSystem=strict
ProtectHome=yes
ProtectControlGroups=yes
ProtectKernelLogs=yes
ProtectKernelModules=yes
ProtectKernelTunables=yes
LockPersonality=yes
MemoryDenyWriteExecute=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
RestrictRealtime=yes
RestrictNamespaces=yes
RestrictSUIDSGID=yes
SystemCallArchitectures=native
ReadOnlyPaths=${DEPLOY_PATH}
ReadWritePaths=${DATA_PATH}
ReadOnlyPaths=/etc/ssl /usr/share/ca-certificates /etc/ca-certificates /usr/share/zoneinfo
ProtectHostname=yes
ProcSubset=pid
ProtectClock=yes
ProtectProc=invisible

[Install]
WantedBy=multi-user.target
EOF
  else
    install -m 0644 "$unit_src" "$unit_dst"
  fi

  # Adjust for venv if USE_UV=false
  if [[ "$USE_UV" != "true" ]]; then
    if [[ ! -x "$VENV_PY" ]]; then
      echo "[INFO] Creating venv and installing deps for dashboard"
      ensure_package python3-venv
      python3 -m venv "${DEPLOY_PATH}/.venv"
      "${DEPLOY_PATH}/.venv/bin/pip" install -U pip
      if [[ -f "$DEPLOY_PATH/pyproject.toml" ]]; then
        "${DEPLOY_PATH}/.venv/bin/pip" install -e "$DEPLOY_PATH"
      fi
    fi
    sed -i "s|^ExecStart=.*|ExecStart=${VENV_PY} ${DEPLOY_PATH}/dashboard.py --host 127.0.0.1 --port ${APP_PORT}|" "$unit_dst"
  fi

  systemctl daemon-reload
  systemctl enable --now ttslo-dashboard || true
  systemctl status --no-pager --lines=5 ttslo-dashboard || true
  echo "[OK] TTSLO Dashboard service installed and started (localhost)."
}

#########################################
# 6) Optional: fail2ban for sshd         #
#########################################
configure_fail2ban() {
  if [[ "$ENABLE_FAIL2BAN" != "true" ]]; then
    echo "[INFO] Skipping fail2ban (ENABLE_FAIL2BAN=false)"
    return 0
  fi
  echo "[STEP] Installing fail2ban for sshd"
  ensure_package fail2ban

  local jaild="/etc/fail2ban/jail.d/ttslo-ssh.conf"
  cat > "$jaild" <<'EOF'
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 5
bantime = 15m
findtime = 15m
EOF
  systemctl enable --now fail2ban
  systemctl restart fail2ban
  echo "[OK] fail2ban configured for sshd."
}

main() {
  require_root

  # Ubuntu version check
  if ! grep -qi "Ubuntu" /etc/os-release; then
    echo "[WARN] This script is designed for Ubuntu. Continuing anyway..."
  fi

  configure_sshd
  configure_pam_faillock
  configure_ufw
  configure_nginx_dashboard
  configure_systemd_service
  configure_dashboard_service
  configure_fail2ban

  echo
  echo "[DONE] Security hardening applied. Quick summary:"
  echo "- SSH is key-only (console password login still works for ${ADMIN_USER})"
  echo "- PAM lockouts active: deny=5, unlock_time=900s (ssh + sudo)"
  echo "- UFW enabled; SSH allowed and rate-limited; dashboard ${DASHBOARD_PUBLIC_PORT} (nginx) allowed only from 192.168.0.0/24; proxied to app on ${APP_PORT}"
  echo "- Nginx proxy with Basic Auth in front of dashboard (password printed above if generated)"
  echo "- TTSLO runs as systemd service user '${SERVICE_USER}' with sandboxing"
  echo
  echo "Revert with: ./remove-security-harden.sh"
}

main "$@"
