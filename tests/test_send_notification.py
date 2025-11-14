from notifications import NotificationManager
from creds import load_env
import os

if __name__ == "__main__":
    # Load environment from /etc/ttslo
    load_env('/etc/ttslo/ttslo.env')
    
    # Check environment
    print(f"TELEGRAM_BOT_TOKEN present: {bool(os.getenv('TELEGRAM_BOT_TOKEN'))}")
    print(f"copilot_TELEGRAM_BOT_TOKEN present: {bool(os.getenv('copilot_TELEGRAM_BOT_TOKEN'))}")
    
    # Simulate service started event
    nm = NotificationManager("notifications.ini")
    print(f"\nNotificationManager initialized:")
    print(f"  enabled: {nm.enabled}")
    print(f"  recipients: {nm.recipients}")
    print(f"  token present: {bool(nm.telegram_token)}")
    
    if nm.enabled:
        print("\n--- Testing service_started ---")
        nm.notify_service_started(service_name="TTSLO Test Service", host="localhost", port=8080)
        
        print("\n--- Testing service_stopped ---")
        nm.notify_service_stopped(service_name="TTSLO Test Service", reason="Test shutdown")
        
        print("\n--- Testing config_changed ---")
        nm.notify_config_changed()
    else:
        print("\n⚠️ Notifications are disabled. Check TELEGRAM_BOT_TOKEN in /etc/ttslo/ttslo.env")
