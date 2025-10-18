# TTSLO Standard Operating Procedure (SOP)

This short, friendly guide covers day‑to‑day use.

Services you will manage:
- ttslo (main trading logic)
- ttslo-dashboard (web UI on port 5080 via nginx)

Key files:
- Config: /var/lib/ttslo/config.csv
- Notifications (optional): /opt/ttslo/notifications.ini
- Env (secrets): /etc/ttslo/ttslo.env (Telegram + Kraken keys)
- Logs: /var/lib/ttslo/logs.csv

---

## 1) Stop the service
Run this before editing your config.

```bash
sudo systemctl stop ttslo ttslo-dashboard
```

---

## 2) Edit your config (and notifications, optional)

Back up and edit your trading config:
```bash
sudo cp /var/lib/ttslo/config.csv /var/lib/ttslo/config.csv.bak.$(date +%F)
sudoedit /var/lib/ttslo/config.csv
```

Optional: enable/adjust Telegram notifications:
```bash
# First time only (creates a working file from the example)
sudo cp /opt/ttslo/notifications.ini.example /opt/ttslo/notifications.ini

# Edit who gets which messages
sudoedit /opt/ttslo/notifications.ini
```
What to put in notifications.ini:
- In [recipients], add your Telegram username and chat_id (get chat_id by messaging @userinfobot).
  Example:
  
  [recipients]
  alice = 123456789
  
- In sections like [notify.config_changed], list the usernames to notify:
  
  [notify.config_changed]
  users = alice

---

## 3) Where to put your Telegram bot token (keys)

Put your Telegram bot token in the env file used by the services:
```bash
sudoedit /etc/ttslo/ttslo.env
```
Add or update this line:
```
TELEGRAM_BOT_TOKEN=1234567890:ABCDEF_your_bot_token_here
```
Notes:
- This same file also stores your Kraken API keys (KRAKEN_API_KEY*).
- Permissions should be root:ttslo 0640 (normally already set):
```bash
sudo chgrp ttslo /etc/ttslo/ttslo.env
sudo chmod 640 /etc/ttslo/ttslo.env
```

---

## 4) Restart the service
```bash
sudo systemctl restart ttslo
sudo systemctl restart ttslo-dashboard
```

Quick checks:
```bash
systemctl is-active ttslo ttslo-dashboard
journalctl -u ttslo -n 50 --no-pager
```

---

## 5) Confirm it is working

If notifications are set up:
- You will receive a Telegram message when the config is reloaded.
- If your config has validation errors, you will receive a Telegram error summary instead.

Dashboard (status UI):
- From your LAN: open http://<this-machine-LAN-ip>:5080
- Login with the Basic Auth credentials shown during the security hardening step.
- The firewall (UFW) allows this port only from your LAN by default.

---

## Troubleshooting (quick)

No Telegram message?
- Check your bot token in /etc/ttslo/ttslo.env
- Check your /opt/ttslo/notifications.ini recipients and users = lists
- View logs: journalctl -u ttslo -n 100 --no-pager

Service not starting?
- systemctl status ttslo ttslo-dashboard
- Read errors in recent logs.

Forgot dashboard password?
- Ask your admin to reset the nginx basic auth password (htpasswd) or rerun the helper.

---

## Quick reference

Stop services:
```bash
sudo systemctl stop ttslo ttslo-dashboard
```
Edit config:
```bash
sudoedit /var/lib/ttslo/config.csv
```
Edit notifications:
```bash
sudoedit /opt/ttslo/notifications.ini
```
Telegram bot token:
```bash
sudoedit /etc/ttslo/ttslo.env
# TELEGRAM_BOT_TOKEN=...
```
Restart:
```bash
sudo systemctl restart ttslo ttslo-dashboard
```
Health:
```bash
systemctl is-active ttslo ttslo-dashboard
journalctl -u ttslo -n 50 --no-pager
```
