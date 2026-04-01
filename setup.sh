#!/usr/bin/env bash
# MiniFMS Raspberry Pi Router Setup Script
# Configures the Pi as a VLAN router with DHCP, DNS, NAT, and firewall.
#
# WARNING: This script changes the network configuration. If you are connected
# via SSH, you may lose connectivity. Run this with physical console access or
# ensure you have an alternative way to recover.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${SCRIPT_DIR}/config"

# --- Preflight checks ---

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: This script must be run as root (use sudo)." >&2
    exit 1
fi

if [[ ! -d "${CONFIG_DIR}/networkd" ]]; then
    echo "ERROR: Config directory not found at ${CONFIG_DIR}/networkd" >&2
    exit 1
fi

echo "===================================="
echo " MiniFMS Router Setup"
echo "===================================="
echo ""
echo "This will configure the Raspberry Pi as a VLAN router with:"
echo "  - Robot VLANs: 10, 20, 30, 40, 50, 60"
echo "  - LAN VLAN: 100 (10.0.100.5)"
echo "  - WAN VLAN: 150 (DHCP client)"
echo ""
echo "WARNING: Network configuration will be replaced."
echo "         Ensure you have console access if running remotely."
echo ""
read -rp "Continue? [y/N] " confirm
if [[ "${confirm}" != "y" && "${confirm}" != "Y" ]]; then
    echo "Aborted."
    exit 0
fi

# --- Install packages ---

echo ""
echo "[1/7] Installing required packages..."
apt-get update -qq
apt-get install -y -qq dnsmasq nftables vlan

# --- Load 8021q VLAN kernel module ---

echo "[2/7] Loading 802.1Q VLAN module..."
modprobe 8021q
if ! grep -q '^8021q$' /etc/modules 2>/dev/null; then
    echo "8021q" >> /etc/modules
fi

# --- Enable IP forwarding ---

echo "[3/7] Enabling IP forwarding..."
cp "${CONFIG_DIR}/sysctl-router.conf" /etc/sysctl.d/99-router.conf
sysctl -p /etc/sysctl.d/99-router.conf

# --- Disable conflicting network managers ---

echo "[4/7] Configuring network stack..."

# Disable NetworkManager if present
if systemctl is-active --quiet NetworkManager 2>/dev/null; then
    systemctl stop NetworkManager
    systemctl disable NetworkManager
    echo "  Disabled NetworkManager"
fi

# Disable dhcpcd if present
if systemctl is-active --quiet dhcpcd 2>/dev/null; then
    systemctl stop dhcpcd
    systemctl disable dhcpcd
    echo "  Disabled dhcpcd"
fi

# Disable systemd-resolved to avoid port 53 conflict with dnsmasq
if systemctl is-active --quiet systemd-resolved 2>/dev/null; then
    systemctl stop systemd-resolved
    systemctl disable systemd-resolved
    # Point resolv.conf to localhost (dnsmasq will serve DNS)
    rm -f /etc/resolv.conf
    echo "nameserver 127.0.0.1" > /etc/resolv.conf
    echo "  Disabled systemd-resolved"
fi

# --- Install systemd-networkd configuration ---

echo "[5/7] Installing network configuration..."

# Clean existing networkd configs
rm -f /etc/systemd/network/*.netdev
rm -f /etc/systemd/network/*.network

# Copy VLAN and network configs
cp "${CONFIG_DIR}"/networkd/*.netdev /etc/systemd/network/
cp "${CONFIG_DIR}"/networkd/*.network /etc/systemd/network/

# Enable systemd-networkd
systemctl enable systemd-networkd

# --- Install dnsmasq configuration ---

echo "[6/7] Installing DHCP/DNS configuration..."

# Backup original config if it exists and hasn't been backed up
if [[ -f /etc/dnsmasq.conf && ! -f /etc/dnsmasq.conf.orig ]]; then
    cp /etc/dnsmasq.conf /etc/dnsmasq.conf.orig
fi

cp "${CONFIG_DIR}/dnsmasq.conf" /etc/dnsmasq.conf

systemctl enable dnsmasq

# --- Install nftables firewall ---

echo "[7/7] Installing firewall rules..."

# Backup original config if it exists and hasn't been backed up
if [[ -f /etc/nftables.conf && ! -f /etc/nftables.conf.orig ]]; then
    cp /etc/nftables.conf /etc/nftables.conf.orig
fi

cp "${CONFIG_DIR}/nftables.conf" /etc/nftables.conf

systemctl enable nftables

# --- Apply everything ---

echo ""
echo "Restarting services..."
systemctl restart systemd-networkd
sleep 2
systemctl restart nftables
systemctl restart dnsmasq

echo ""
echo "===================================="
echo " Setup Complete"
echo "===================================="
echo ""
echo "Network Configuration:"
echo "  eth0.10  -> VLAN 10  (Robot) 10.0.10.4/24   DHCP: .100-.155"
echo "  eth0.20  -> VLAN 20  (Robot) 10.0.20.4/24   DHCP: .100-.155"
echo "  eth0.30  -> VLAN 30  (Robot) 10.0.30.4/24   DHCP: .100-.155"
echo "  eth0.40  -> VLAN 40  (Robot) 10.0.40.4/24   DHCP: .100-.155"
echo "  eth0.50  -> VLAN 50  (Robot) 10.0.50.4/24   DHCP: .100-.155"
echo "  eth0.60  -> VLAN 60  (Robot) 10.0.60.4/24   DHCP: .100-.155"
echo "  eth0.100 -> VLAN 100 (LAN)   10.0.100.5/24  DHCP: .50-.200"
echo "  eth0.150 -> VLAN 150 (WAN)   DHCP client"
echo "  eth0.200 -> VLAN 200 (Switch Config) 192.168.0.50/24"
echo ""
echo "Firewall:"
echo "  LAN -> WAN: Full internet access (NAT)"
echo "  Robot -> LAN: UDP 1145->1160, TCP 1750, ICMP only"
echo "  Robot <-> Robot: Isolated (ICMP to x.x.x.4 only)"
echo ""
echo "Verify with:"
echo "  ip -br addr              # Check interface IPs"
echo "  nft list ruleset          # Check firewall rules"
echo "  systemctl status dnsmasq  # Check DHCP/DNS"
echo "  journalctl -u dnsmasq    # DHCP lease logs"
