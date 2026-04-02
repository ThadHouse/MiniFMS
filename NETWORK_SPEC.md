# MiniFMS Network Specification

## Overview
Raspberry Pi configured as a VLAN router for FRC-style robot field management. Uses systemd-networkd, dnsmasq, and nftables.

## VLANs

### Robot VLANs (6 total, isolated)
- VLAN IDs: 10, 20, 30, 40, 50, 60, 70, 80
- Subnets: 10.0.X.0/24 (where X = VLAN ID)
- Pi gateway address: 10.0.X.4
- DHCP range: 10.0.X.100 - 10.0.X.155
- Isolated from each other and from the internet

### LAN (VLAN 100)
- Subnet: 10.0.100.0/24
- Pi static IP: 10.0.100.5
- DHCP range: 10.0.100.50 - 10.0.100.200
- Has internet access via WAN (NAT)

### WAN (VLAN 150)
- Connected to external network
- Pi is a DHCP client on this VLAN
- Used for LAN internet access (NAT masquerade)

## Firewall Rules (Robot VLAN -> LAN allowed traffic)
Derived from Cisco switch ACLs:
- `permit udp any 10.0.100.0/24 eq 1160` — UDP to LAN port 1160 from any source port
- `permit tcp any 10.0.100.0/24 eq 1750` — TCP to LAN port 1750
- `permit icmp any 10.0.100.0/24` — ICMP (ping) to LAN
- `permit icmp any 10.0.0.4 0.255.255.0` — ICMP to any 10.x.x.4 (gateway addresses across VLANs)
- `permit udp any any eq bootpc` / `permit udp any any eq bootps` — DHCP allowed everywhere

## Original Cisco ACL (for reference)
```
permit udp any eq 1145 10.0.100.0 0.0.0.255 eq 1160
permit tcp any 10.0.100.0 0.0.0.255 eq 1750
permit icmp any 10.0.100.0 0.0.0.255
permit icmp any 10.0.0.4 0.255.255.0
permit udp any any eq bootpc
permit udp any any eq bootps
```
Note: The original ACL had `any eq 1145` as source port constraint on the UDP 1160 rule, but this was intentionally changed to allow any source port.

## Key Config Files
- `config/networkd/` — systemd-networkd VLAN netdev and network files
- `config/dnsmasq.conf` — DHCP/DNS server
- `config/nftables.conf` — Firewall and NAT rules
- `config/sysctl-router.conf` — IP forwarding
- `setup.sh` — Main installation script

## Technical Details
- Base interface: eth0 (802.1Q trunk)
- VLAN interfaces: eth0.{10,20,30,40,50,60,70,80,100,150}
- DNS upstream: 8.8.8.8, 1.1.1.1
- SSH allowed from LAN only (port 22)
- Services: systemd-networkd, dnsmasq, nftables
- Disables: NetworkManager, dhcpcd, systemd-resolved
