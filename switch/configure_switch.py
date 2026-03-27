#!/usr/bin/env python3
"""
Configure a TP-Link TL-SG108E switch with a MiniFMS VLAN profile.

Usage:
    python3 configure_switch.py <profile> <switch_ip> [--password <password>]

Profiles:
    robot_a  - VLANs 10,20,30,40 + LAN(100) + WAN(150), trunk on 7-8
    robot_b  - VLANs 50,60,70,80 + LAN(100), trunk on 7-8
    lan      - LAN(100) on ports 1-6, trunk on 7-8

Examples:
    python3 configure_switch.py robot_a 192.168.0.1
    python3 configure_switch.py robot_b 192.168.0.2 --password secret
    python3 configure_switch.py lan 192.168.0.3

Requirements:
    pip install requests
"""

import argparse
import sys

from profiles import PROFILES
from sg108e import SG108E


def print_profile_summary(name, profile):
    """Print a human-readable summary of a profile before applying."""
    print(f"Profile: {name}")
    print("-" * 50)
    for vlan in profile["vlans"]:
        if not vlan["tagged"] and not vlan["untagged"]:
            continue
        tagged = ",".join(str(p) for p in vlan["tagged"]) or "-"
        untagged = ",".join(str(p) for p in vlan["untagged"]) or "-"
        print(
            f"  VLAN {vlan['id']:>4} ({vlan['name']:<10}): "
            f"access=[{untagged}]  trunk=[{tagged}]"
        )
    print()
    print("  Port PVIDs:")
    for port in range(1, 9):
        pvid = profile["pvids"].get(port, 1)
        print(f"    Port {port} -> VLAN {pvid}")
    print("-" * 50)


def main():
    parser = argparse.ArgumentParser(
        description="Configure a TL-SG108E switch for MiniFMS"
    )
    parser.add_argument(
        "profile",
        choices=list(PROFILES.keys()),
        help="Switch profile to apply",
    )
    parser.add_argument("host", help="Switch IP address")
    parser.add_argument(
        "--password", default="admin", help="Switch admin password (default: admin)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the profile without applying",
    )

    args = parser.parse_args()

    profile = PROFILES[args.profile]
    print()
    print_profile_summary(args.profile, profile)

    if args.dry_run:
        print("Dry run mode - no changes applied.")
        return

    print()
    confirm = input(f"Apply profile '{args.profile}' to {args.host}? [y/N] ")
    if confirm.lower() != "y":
        print("Aborted.")
        sys.exit(0)

    print()
    switch = SG108E(host=args.host, password=args.password)
    try:
        switch.apply_profile(profile)
        print()
        print("Switch configured successfully.")
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        print(
            "\nNote: The TL-SG108E web API varies by hardware/firmware version.",
            file=sys.stderr,
        )
        print(
            "You may need to adjust switch/sg108e.py for your specific model.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
