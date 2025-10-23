#!/usr/bin/env python3
"""
Test script to verify IP detection in dashboard notification.
This simulates what dashboard.py does when sending service_started notification.
"""
import socket


def get_host_ip_for_notification(bind_host):
    """
    Simulate the IP detection logic from dashboard.py.
    Returns the IP address that would be used in the notification.
    """
    if bind_host in ('0.0.0.0', '::'):
        # Get the actual server IP address by creating a socket connection
        # This gives us the actual LAN IP that would be used for outbound connections
        try:
            # Create a UDP socket (doesn't actually send data)
            # Connect to a public DNS server to determine our local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            host_ip = s.getsockname()[0]
            s.close()
        except Exception:
            # Fallback: try to get IP from network interfaces
            try:
                hostname = socket.gethostname()
                # Get all IP addresses for this host
                all_ips = socket.getaddrinfo(hostname, None)
                
                # Filter to IPv4 addresses only
                ipv4_addresses = [ip[4][0] for ip in all_ips if ip[0] == socket.AF_INET]
                
                # Prioritize 192.168.x.x and 10.x.x.x addresses (private networks)
                local_ips = [ip for ip in ipv4_addresses if ip.startswith('192.168.') or ip.startswith('10.')]
                if local_ips:
                    host_ip = local_ips[0]
                elif ipv4_addresses:
                    # Use first non-localhost IP
                    non_localhost = [ip for ip in ipv4_addresses if not ip.startswith('127.')]
                    host_ip = non_localhost[0] if non_localhost else ipv4_addresses[0]
                else:
                    host_ip = '127.0.0.1'
            except Exception:
                host_ip = '127.0.0.1'
    else:
        host_ip = bind_host
    
    return host_ip


def main():
    print("Testing Dashboard IP Detection")
    print("=" * 50)
    print()
    
    # Test with different bind addresses
    test_cases = [
        ('0.0.0.0', 5000),
        ('127.0.0.1', 5000),
        ('::', 5000),
        ('192.168.1.100', 8080),
    ]
    
    for bind_host, port in test_cases:
        detected_ip = get_host_ip_for_notification(bind_host)
        url = f"http://{detected_ip}:{port}"
        
        print(f"Bind Host: {bind_host}")
        print(f"Detected IP: {detected_ip}")
        print(f"URL in notification: {url}")
        
        # Check if it's localhost
        is_localhost = detected_ip.startswith('127.')
        if bind_host in ('0.0.0.0', '::'):
            if is_localhost:
                print("⚠️  WARNING: Detected localhost IP when binding to all interfaces")
                print("   This means the notification will show 127.x.x.x instead of LAN IP")
            else:
                print("✓ Good: Non-localhost IP detected for 0.0.0.0 binding")
        else:
            print("✓ Using specified bind address")
        
        print()
    
    print("=" * 50)
    print("\nExpected behavior:")
    print("- When binding to 0.0.0.0, should show LAN IP (e.g., 192.168.x.x or 10.x.x.x)")
    print("- When binding to specific IP, should show that IP")
    print("- Should NOT show 127.0.1.1 or other localhost addresses")


if __name__ == '__main__':
    main()
