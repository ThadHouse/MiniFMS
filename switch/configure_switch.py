#!/usr/bin/env python3
"""
Configure a TP-Link TL-SG108E switch with a MiniFMS VLAN profile.

Usage:
    python3 configure_switch.py <profile> [--password <password>]

The switch is expected to be at 192.168.0.1 (factory default).
The admin password will be set to 'minifms' (override with --password).
After configuration, the switch will be assigned a new static IP:
    robot_a  -> 10.0.100.10
    robot_b  -> 10.0.100.11
    lan      -> 10.0.100.12

Profiles:
    robot_a  - VLANs 10,20,30,40 + LAN(100) + WAN(150), trunk on 7-8
    robot_b  - VLANs 50,60,70,80 + LAN(100), trunk on 7-8
    lan      - LAN(100) on ports 1-6, trunk on 7-8

Examples:
    python3 configure_switch.py robot_a
    python3 configure_switch.py robot_b --password secret
    python3 configure_switch.py lan

Requirements:
    pip install requests
"""

import argparse
import sys

from profiles import PROFILES, SWITCH_IPS
from sg108e import SG108E

FACTORY_IP = "192.168.0.1"


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
    parser.add_argument(
        "--password", default="minifms", help="Switch admin password (default: minifms)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the profile without applying",
    )

    args = parser.parse_args()

    profile = PROFILES[args.profile]
    new_ip = SWITCH_IPS[args.profile]
    print()
    print_profile_summary(args.profile, profile)
    print(f"  New switch IP: {new_ip}")

    if args.dry_run:
        print("Dry run mode - no changes applied.")
        return

    print()
    confirm = input(
        f"Apply profile '{args.profile}' to {FACTORY_IP} "
        f"(new IP: {new_ip})? [y/N] "
    )
    if confirm.lower() != "y":
        print("Aborted.")
        sys.exit(0)

    print()
    switch = SG108E(host=FACTORY_IP, password=args.password)
    try:
        switch.apply_profile(profile, new_ip=new_ip)
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
