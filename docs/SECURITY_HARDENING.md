# Ubuntu 24.04 Server Hardening for TTSLO

This guide provides a practical, production-focused hardening checklist for running TTSLO on Ubuntu 24.04 with sensitive Kraken API keys.

Key goals:
- Reduce attack surface (SSH, users, network)
- Prevent brute‑force and credential stuffing
- Isolate the app and its secrets with systemd sandboxing
- Enable safe defaults and easy recovery

## 1) Accounts and sudo

- Create a dedicated, non‑login service account:
  - user: `ttslo` (no shell, no password)
  - group: `ttslo`
- Keep your admin account with sudo; lock it down via SSH controls and PAM lockouts (below).
- Do not run the service as your admin/sudo user.

Commands (example):
- Create user/group: `sudo adduser --system --home /var/lib/ttslo --group --shell /usr/sbin/nologin ttslo`
- Create state/log dirs: `sudo install -d -o ttslo -g ttslo -m 0750 /var/lib/ttslo`
- Place code under `/opt/ttslo` read‑only: `sudo install -d -o root -g root -m 0755 /opt/ttslo` and deploy files there.

## 2) SSH hardening

- Disable password auth; use SSH keys only.
- Consider 2FA (U2F/sk-ecdsa/ed25519-sk keys) or TOTP for sudo.
- Optionally restrict SSH by IP with UFW or move SSH to a non‑standard port (minor obfuscation only).
- Optionally require a VPN (WireGuard) and bind SSH to the WG interface only.

Recommended `sshd_config` changes:
- `PasswordAuthentication no`
- `KbdInteractiveAuthentication no`
- `PermitRootLogin no`
- `PubkeyAuthentication yes`
- `MaxAuthTries 3`
- `ClientAliveInterval 300` and `ClientAliveCountMax 2`
- `AllowUsers youradminuser`

Then restart ssh: `sudo systemctl reload ssh`.

## 3) PAM lockouts (failed attempts)

Use `pam_faillock` for temporary lockouts after repeated failures. This protects both SSH and sudo.

- Install (usually present): `sudo apt-get install libpam-modules`
- Edit `/etc/pam.d/common-auth` and add at the top:
  - `auth required pam_faillock.so preauth silent deny=5 unlock_time=900`  (15 min)
  - `auth [success=1 default=bad] pam_unix.so`
  - `auth [default=die] pam_faillock.so authfail deny=5 unlock_time=900`
  - `auth sufficient pam_faillock.so authsucc`
- Edit `/etc/pam.d/sudo` similarly (conservative):
  - `auth required pam_faillock.so preauth silent deny=5 unlock_time=900`
  - `auth [success=1 default=bad] pam_unix.so`
  - `auth [default=die] pam_faillock.so authfail deny=5 unlock_time=900`
  - `auth sufficient pam_faillock.so authsucc`

Recovery: if you lock yourself out, use console/serial/KVM to log in as root or via recovery mode and run `pam_faillock --user youradminuser --reset`.

Alternative/additional: `fail2ban` to ban abusive IPs at the firewall level.

## 4) UFW rules

You already enabled UFW. Suggested baseline:
- Default deny incoming, allow outgoing
- Allow SSH from your IP(s) or VPN subnet only
- Only open additional ports if needed (e.g., local dashboard); otherwise bind services to localhost

Example:
- `sudo ufw default deny incoming`
- `sudo ufw default allow outgoing`
- `sudo ufw allow from your.ip.addr.0/24 to any port 22 proto tcp`
- `sudo ufw enable`

## 5) Service isolation with systemd

Use the provided hardened unit `deploy/systemd/ttslo.service`:
- Runs as user `ttslo` with no shell
- Sandboxes filesystem, devices, tmp
- Read‑only code under `/opt/ttslo`, read/write state under `/var/lib/ttslo`
- Reads secrets from `/etc/ttslo/ttslo.env` (root:ttslo 0640)

Steps:
1) Deploy code to `/opt/ttslo` (root‑owned, 0755). Keep git working dir here or copy a release bundle.
2) Create env dir and file:
   - `sudo install -d -o root -g ttslo -m 0750 /etc/ttslo`
   - `sudo install -o root -g ttslo -m 0640 deploy/systemd/ttslo.env.example /etc/ttslo/ttslo.env`
   - Edit and set keys.
3) Create data dirs:
   - `sudo install -d -o ttslo -g ttslo -m 0750 /var/lib/ttslo`
   - Touch config/state/log files as needed and `chown ttslo:ttslo`.
4) Install unit:
   - `sudo install -m 0644 deploy/systemd/ttslo.service /etc/systemd/system/ttslo.service`
   - `sudo systemctl daemon-reload`
   - `sudo systemctl enable --now ttslo`

Verify: `systemctl status ttslo` and `journalctl -u ttslo -f`.

## 6) Secrets handling

Baseline: root‑owned env file, group‐readable by `ttslo` only.
- Path: `/etc/ttslo/ttslo.env`
- Perms: `0640`, owner `root`, group `ttslo`

What to put in it (Kraken API):
```
KRAKEN_API_KEY=...            # read-only key
KRAKEN_API_SECRET=...
KRAKEN_API_KEY_RW=...         # read-write key (Create & Modify Orders only)
KRAKEN_API_SECRET_RW=...
```
This env file is read by the systemd services via `EnvironmentFile=/etc/ttslo/ttslo.env`. Keep it off git and back it up securely. Rotate by editing the file and restarting the service(s): `sudo systemctl restart ttslo ttslo-dashboard`.

Upgrades:
- systemd-creds (if available): `systemd-creds encrypt` to store sealed env fragments and reference via `LoadCredential=` and `SetCredential=`.
- sops-age/PGP to encrypt a repo‑committed `ttslo.env.enc` and decrypt on deploy.
- Hardware tokens/HSM for storing secrets are overkill unless you rotate keys frequently.

Kraken side:
- Use two keys (RO and RW). Limit RW to "Create & Modify Orders" only.
- Consider IP whitelisting if Kraken offers and your IP is static.

## 7) Optional dashboard exposure

The Flask dashboard is for local use. If you must expose it:
- Put it behind a reverse proxy (nginx) with basic auth or OAuth, and TLS
- Bind Flask to 127.0.0.1 and let nginx do TLS/Internet
- Or expose only through a VPN (WireGuard) and keep it closed to the public Internet

## 8) Patching, auditing, and monitoring

- Enable unattended security upgrades: `sudo apt-get install unattended-upgrades` and configure
- Baseline packages: `fail2ban`, `auditd`
- Time sync: `systemd-timesyncd` (default) or `chrony`
- Log review: `journalctl -u ttslo` and CSV logs under `/var/lib/ttslo`
- Backups: off‑box backups of `/var/lib/ttslo` and deployment repo

## 9) Kernel/network hygiene (light‑touch)

- Disable source routing and ICMP redirects; basic SYN flood tuning.
- Place a simple `/etc/sysctl.d/99-ttslo.conf` with reasonable defaults:
```
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.tcp_syncookies = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv6.conf.all.accept_redirects = 0
```
Then `sudo sysctl --system`.

## 10) Recovery and ops tips

- Keep a console/KVM path for emergencies (in case PAM lockouts or SSH bans trigger).
- Store a break‑glass SSH key offline; test access.
- Document a secret rotation procedure (replace `/etc/ttslo/ttslo.env`, `systemctl restart ttslo`).
- Dry‑run mode is safe; when enabling RW keys, start during low‑risk hours and monitor.

## Appendix: Choosing an access model

- Single admin with sudo on host: OK if SSH is key‑only, PAM lockouts enabled, and IP restricted.
- Service user locked down + systemd sandboxing: strongly recommended.
- Console‑only requirement: high friction; good for high‑risk periods. Combine with VPN for balance.
- VPN‑only SSH: excellent balance of usability and security.

Questions or improvements? See `SECURITY.md` and open an issue.
