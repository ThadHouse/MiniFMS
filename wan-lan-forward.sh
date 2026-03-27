#!/usr/bin/env bash
# Enable/disable port forwarding from WAN to LAN (10.0.100.5)
# Forwards: SSH (22), HTTP (80), HTTP-alt (8080)
set -euo pipefail

LAN_IP="10.0.100.5"
WAN_IFACE="eth0.150"
PORTS="22 80 8080"

usage() {
    echo "Usage: $0 {enable|disable|status}"
    echo ""
    echo "Forwards ports 22, 80, 8080 from WAN to LAN ($LAN_IP)"
    exit 1
}

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: Must be run as root (use sudo)." >&2
    exit 1
fi

[[ $# -ge 1 ]] || usage

case "$1" in
    enable)
        # Add DNAT rules for each port
        for port in $PORTS; do
            nft add rule inet nat prerouting iifname "$WAN_IFACE" tcp dport "$port" dnat to "$LAN_IP":"$port"
        done

        # Allow forwarded traffic through the firewall
        for port in $PORTS; do
            nft add rule inet filter forward iifname "$WAN_IFACE" ip daddr "$LAN_IP" tcp dport "$port" ct state new accept \
                comment \"wan-lan-fwd-$port\"
        done

        echo "Port forwarding ENABLED: WAN -> $LAN_IP"
        echo "  Ports: ${PORTS}"
        ;;

    disable)
        # Flush and recreate the prerouting chain (removes DNAT rules)
        # We re-add the chain definition since flushing removes all rules
        nft flush chain inet nat prerouting 2>/dev/null || true

        # Remove the forwarding rules by comment
        for port in $PORTS; do
            HANDLE=$(nft -a list chain inet filter forward 2>/dev/null \
                | grep "wan-lan-fwd-$port" \
                | awk '{print $NF}')
            if [[ -n "$HANDLE" ]]; then
                nft delete rule inet filter forward handle "$HANDLE"
            fi
        done

        echo "Port forwarding DISABLED: WAN -> $LAN_IP"
        ;;

    status)
        echo "=== NAT prerouting rules ==="
        nft list chain inet nat prerouting 2>/dev/null || echo "(no prerouting chain)"
        echo ""
        echo "=== Forward rules with wan-lan-fwd ==="
        nft list chain inet filter forward 2>/dev/null | grep "wan-lan-fwd" || echo "(none)"
        ;;

    *)
        usage
        ;;
esac
