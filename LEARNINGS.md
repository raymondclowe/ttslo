# LEARNINGS

Key learnings and gotchas discovered during TTSLO development.

## IP Detection for Network Services

**Problem**: When binding Flask/web services to `0.0.0.0`, `socket.gethostname()` and `socket.getaddrinfo()` may return localhost IPs like `127.0.1.1` instead of the actual LAN IP.

**Solution**: Use UDP socket connection to external IP to determine local interface IP:
```python
import socket

# Primary method - works reliably
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(('8.8.8.8', 80))  # Doesn't send data, just determines routing
host_ip = s.getsockname()[0]
s.close()
```

**Why this works**: 
- Creating a UDP socket and "connecting" to an external IP (like Google DNS 8.8.8.8) forces the OS to determine which local network interface would be used
- The socket's local address (`getsockname()[0]`) is the actual LAN IP
- No data is actually sent (UDP connect is just routing info)

**Fallback strategy**:
1. Try UDP socket method first (most reliable)
2. Fall back to `socket.getaddrinfo()` with enhanced filtering
3. Filter out ALL `127.x.x.x` addresses (not just `127.0.0.1`)
4. Prioritize private network ranges: `192.168.x.x` and `10.x.x.x`
5. Accept `172.16.x.x` through `172.31.x.x` as private networks too

**Related files**:
- `dashboard.py`: Lines 488-525 (notification IP detection)
- `test_ip_detection.py`: Unit tests for IP detection methods
- `test_dashboard_ip_detection.py`: End-to-end verification

**Testing**: Verify with `python3 test_dashboard_ip_detection.py` to see actual IPs detected.

---

## Network Security Best Practices

When binding services to `0.0.0.0`:
- Use firewall rules to restrict access to local subnet only
- Example (UFW): `sudo ufw allow from 192.168.1.0/24 to any port 5000`
- Example (iptables): `sudo iptables -A INPUT -p tcp --dport 5000 -s 192.168.1.0/24 -j ACCEPT`
- Document security expectations in README
- Systemd services should run as unprivileged users
- Use read-only mode for monitoring/dashboard services

---

*Add new learnings here as we discover them*
