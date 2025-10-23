#!/usr/bin/env python3
"""
Demo script to test Telegram notifications.
This script can be used to verify your Telegram bot setup.
"""
import os
import sys
from notifications import NotificationManager

def main():
    print("TTSLO Telegram Notifications Demo")
    print("=" * 50)
    print()
    
    # Check for bot token
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('copilot_TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ Error: TELEGRAM_BOT_TOKEN environment variable not set")
        print()
        print("To fix this:")
        print("1. Create a bot by messaging @BotFather on Telegram")
        print("2. Add TELEGRAM_BOT_TOKEN to your .env file")
        print("3. Run this script again")
        return 1
    
    print(f"✓ Bot token found: {bot_token[:10]}...")
    print()
    
    # Check for notifications.ini
    if not os.path.exists('notifications.ini'):
        print("❌ Error: notifications.ini file not found")
        print()
        print("To fix this:")
        print("1. Copy notifications.ini.example to notifications.ini")
        print("2. Add your chat ID to the [recipients] section")
        print("3. Get your chat ID by messaging @userinfobot on Telegram")
        print("4. Run this script again")
        return 1
    
    print("✓ notifications.ini file found")
    print()
    
    # Initialize notification manager
    nm = NotificationManager()
    
    if not nm.enabled:
        print("❌ Error: Notifications are not enabled")
        print()
        print("Possible reasons:")
        print("- No recipients configured in notifications.ini")
        print("- Invalid configuration file format")
        return 1
    
    print(f"✓ Notifications enabled for {len(nm.recipients)} recipient(s):")
    for username in nm.recipients:
        print(f"  - {username}")
    print()
    
    # Show subscriptions
    print("Event subscriptions:")
    if nm.subscriptions:
        for event_type, users in nm.subscriptions.items():
            print(f"  {event_type}: {', '.join(users)}")
    else:
        print("  (none configured)")
    print()
    
    # Offer to send test messages
    print("Would you like to send test notifications?")
    response = input("Type 'yes' to send test messages: ").strip().lower()
    
    if response == 'yes':
        print()
        print("Sending test notifications...")
        print()
        
        # Test 1: Config changed
        print("1. Testing config_changed notification...")
        nm.notify_config_changed()
        print("   Sent!")
        
        # Test 2: Trigger reached
        print("2. Testing trigger_reached notification...")
        nm.notify_trigger_price_reached(
            config_id='demo_test',
            pair='XXBTZUSD',
            current_price=52000.00,
            threshold_price=50000.00,
            threshold_type='above'
        )
        print("   Sent!")
        
        # Test 3: TSL order created
        print("3. Testing tsl_created notification...")
        nm.notify_tsl_order_created(
            config_id='demo_test',
            order_id='DEMO-ORDER-12345',
            pair='XXBTZUSD',
            direction='sell',
            volume='0.01',
            trailing_offset=5.0,
            trigger_price=52000.00
        )
        print("   Sent!")
        
        print()
        print("✅ Test notifications sent!")
        print()
        print("Check your Telegram to see if you received the messages.")
        print("If you didn't receive them, verify:")
        print("- Your chat ID is correct in notifications.ini")
        print("- You've messaged your bot at least once")
        print("- Your bot token is valid")
    else:
        print()
        print("Test notifications not sent.")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
