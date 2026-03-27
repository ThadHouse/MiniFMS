#!/usr/bin/env bash
# Enable/disable port forwarding from WAN to a robot VLAN gateway
# Forwards: SSH (22), HTTP (80), HTTP-alt (8080)
set -euo pipefail

WAN_IFACE="eth0.150"
PORTS="22 80 8080"
VALID_VLANS="10 20 30 40 50 60"

usage() {
    echo "Usage: $0 {enable|disable|status} <vlan>"
    echo ""
    echo "Forwards ports 22, 80, 8080 from WAN to a robot VLAN gateway (10.0.X.4)"
    echo ""
    echo "  vlan: one of $VALID_VLANS"
    echo ""
    echo "Examples:"
    echo "  $0 enable 10     # Forward WAN to 10.0.10.4"
    echo "  $0 disable 10    # Remove forwarding"
    echo "  $0 status 10     # Show current rules for VLAN 10"
    echo "  $0 status all    # Show all robot forwarding rules"
    exit 1
}

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: Must be run as root (use sudo)." >&2
    exit 1
fi

[[ $# -ge 2 ]] || usage

ACTION="$1"
VLAN="$2"

validate_vlan() {
    local v="$1"
    for valid in $VALID_VLANS; do
        [[ "$v" == "$valid" ]] && return 0
    done
    echo "ERROR: Invalid VLAN '$v'. Must be one of: $VALID_VLANS" >&2
    exit 1
}

case "$ACTION" in
    enable)
        validate_vlan "$VLAN"
        TARGET_IP="10.0.${VLAN}.4"
        TAG="wan-robot${VLAN}-fwd"

        for port in $PORTS; do
            nft add rule inet nat prerouting iifname "$WAN_IFACE" tcp dport "$port" dnat to "$TARGET_IP":"$port" \
                comment \"${TAG}-${port}\"
        done

        for port in $PORTS; do
            nft add rule inet filter forward iifname "$WAN_IFACE" ip daddr "$TARGET_IP" tcp dport "$port" ct state new accept \
                comment \"${TAG}-${port}\"
        done

        echo "Port forwarding ENABLED: WAN -> $TARGET_IP (VLAN $VLAN)"
        echo "  Ports: ${PORTS}"
        echo ""
        echo "NOTE: This conflicts with LAN port forwarding if both are enabled."
        echo "      Disable LAN forwarding first: sudo ./wan-lan-forward.sh disable"
        ;;

    disable)
        validate_vlan "$VLAN"
        TARGET_IP="10.0.${VLAN}.4"
        TAG="wan-robot${VLAN}-fwd"

        # Remove NAT rules
        for port in $PORTS; do
            HANDLE=$(nft -a list chain inet nat prerouting 2>/dev/null \
                | grep "${TAG}-${port}" \
                | awk '{print $NF}')
            if [[ -n "$HANDLE" ]]; then
                nft delete rule inet nat prerouting handle "$HANDLE"
            fi
        done

        # Remove forward rules
        for port in $PORTS; do
            HANDLE=$(nft -a list chain inet filter forward 2>/dev/null \
                | grep "${TAG}-${port}" \
                | awk '{print $NF}')
            if [[ -n "$HANDLE" ]]; then
                nft delete rule inet filter forward handle "$HANDLE"
            fi
        done

        echo "Port forwarding DISABLED: WAN -> $TARGET_IP (VLAN $VLAN)"
        ;;

    status)
        if [[ "$VLAN" == "all" ]]; then
            echo "=== All robot VLAN forwarding rules ==="
            echo ""
            echo "--- NAT prerouting ---"
            nft list chain inet nat prerouting 2>/dev/null | grep "wan-robot" || echo "(none)"
            echo ""
            echo "--- Filter forward ---"
            nft list chain inet filter forward 2>/dev/null | grep "wan-robot" || echo "(none)"
        else
            validate_vlan "$VLAN"
            TAG="wan-robot${VLAN}-fwd"
            echo "=== VLAN $VLAN forwarding rules ==="
            echo ""
            echo "--- NAT prerouting ---"
            nft list chain inet nat prerouting 2>/dev/null | grep "$TAG" || echo "(none)"
            echo ""
            echo "--- Filter forward ---"
            nft list chain inet filter forward 2>/dev/null | grep "$TAG" || echo "(none)"
        fi
        ;;

    *)
        usage
        ;;
esac
