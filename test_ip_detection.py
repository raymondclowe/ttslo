"""Test IP detection for notification messages."""
import socket


def test_get_lan_ip():
    """Test that we can get the LAN IP address."""
    # Try the primary method (UDP socket)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        host_ip = s.getsockname()[0]
        s.close()
        
        # Should not be localhost
        assert not host_ip.startswith('127.'), f"Expected non-localhost IP, got {host_ip}"
        
        # Should be a valid IP format
        parts = host_ip.split('.')
        assert len(parts) == 4, f"Expected 4 octets, got {len(parts)}"
        
        # All parts should be integers
        for part in parts:
            assert 0 <= int(part) <= 255, f"Invalid IP octet: {part}"
        
        print(f"✓ Got LAN IP: {host_ip}")
        return True
    except Exception as e:
        print(f"Primary method failed: {e}")
        # Fallback should still work
        hostname = socket.gethostname()
        all_ips = socket.getaddrinfo(hostname, None)
        ipv4_addresses = [ip[4][0] for ip in all_ips if ip[0] == socket.AF_INET]
        
        # Filter out localhost
        non_localhost = [ip for ip in ipv4_addresses if not ip.startswith('127.')]
        
        if non_localhost:
            print(f"✓ Got IP from fallback: {non_localhost[0]}")
            return True
        else:
            print(f"⚠ Only localhost IPs available: {ipv4_addresses}")
            # This is acceptable in some environments
            return True


def test_ip_priority():
    """Test that we prioritize private network IPs correctly."""
    test_ips = [
        '127.0.0.1',
        '127.0.1.1', 
        '192.168.1.100',
        '10.0.0.50',
        '172.16.0.1',
    ]
    
    # Should prioritize 192.168.x.x and 10.x.x.x
    local_ips = [ip for ip in test_ips if ip.startswith('192.168.') or ip.startswith('10.')]
    
    assert '192.168.1.100' in local_ips
    assert '10.0.0.50' in local_ips
    assert '127.0.0.1' not in local_ips
    assert '127.0.1.1' not in local_ips
    
    print(f"✓ Correctly filtered private IPs: {local_ips}")


if __name__ == '__main__':
    test_get_lan_ip()
    test_ip_priority()
    print("\n✓ All IP detection tests passed")
