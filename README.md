# MiniFMS Router Setup

Configures a Raspberry Pi as a VLAN router for FRC-style robot field management.

## Network Layout

| VLAN | Interface | Subnet | Pi Address | DHCP Range | Role |
|------|-----------|--------|------------|------------|------|
| 10 | eth0.10 | 10.0.10.0/24 | 10.0.10.4 | .100 - .155 | Robot |
| 20 | eth0.20 | 10.0.20.0/24 | 10.0.20.4 | .100 - .155 | Robot |
| 30 | eth0.30 | 10.0.30.0/24 | 10.0.30.4 | .100 - .155 | Robot |
| 40 | eth0.40 | 10.0.40.0/24 | 10.0.40.4 | .100 - .155 | Robot |
| 50 | eth0.50 | 10.0.50.0/24 | 10.0.50.4 | .100 - .155 | Robot |
| 60 | eth0.60 | 10.0.60.0/24 | 10.0.60.4 | .100 - .155 | Robot |
| 100 | eth0.100 | 10.0.100.0/24 | 10.0.100.5 | .50 - .200 | LAN |
| 150 | eth0.150 | (external) | DHCP client | — | WAN |

## Firewall Rules

### LAN (VLAN 100)
- Full internet access via WAN (NAT masquerade)
- SSH access to the Pi (port 22)

### Robot VLANs (10–60) → LAN
- UDP to port 1160 (any source port)
- TCP to port 1750
- ICMP (ping)

### Robot VLANs (10–60) → Other
- ICMP to any `10.x.x.4` address (inter-VLAN diagnostics to gateway)
- All other inter-VLAN and internet traffic is **blocked**

### DHCP/DNS
- Allowed on all internal interfaces (robot + LAN)

## Prerequisites

- Raspberry Pi running Raspberry Pi OS (or Debian-based)
- Ethernet connected to a managed switch with 802.1Q VLAN trunking
- Switch must be configured to trunk VLANs 10, 20, 30, 40, 50, 60, 100, 150 to the Pi's port

## Installation

```bash
sudo ./setup.sh
```

The script will:
1. Install `dnsmasq`, `nftables`, and `vlan` packages
2. Load the 802.1Q kernel module
3. Enable IPv4 forwarding
4. Disable conflicting services (NetworkManager, dhcpcd, systemd-resolved)
5. Install systemd-networkd VLAN and interface configs
6. Install dnsmasq DHCP/DNS configuration
7. Install nftables firewall rules
8. Restart all services

## File Structure

```
├── setup.sh                          # Main setup script (run as root)
├── config/
│   ├── dnsmasq.conf                  # DHCP/DNS server configuration
│   ├── nftables.conf                 # Firewall and NAT rules
│   ├── sysctl-router.conf            # IPv4 forwarding
│   └── networkd/
│       ├── 10-eth0.network           # Base interface (VLAN trunk)
│       ├── 20-vlan{10..150}.netdev   # VLAN interface definitions
│       └── 30-vlan{10..150}.network  # VLAN IP address assignments
```

## Verification

After running the setup script:

```bash
# Check interfaces and IPs
ip -br addr

# Check firewall rules
sudo nft list ruleset

# Check DHCP/DNS status
systemctl status dnsmasq

# Monitor DHCP leases
journalctl -fu dnsmasq
```
