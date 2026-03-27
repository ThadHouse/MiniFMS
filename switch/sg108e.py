"""
TP-Link TL-SG108E Easy Smart Switch configuration library.

Communicates with the switch via its HTTP management interface.
Tested against firmware commonly found on TL-SG108E V5/V6 hardware.
May require adaptation for older hardware revisions.
"""

import hashlib
import json
import re
import sys
import requests


class SG108E:
    """Interface to a TL-SG108E switch's web management API."""

    NUM_PORTS = 8

    def __init__(self, host, password="admin", timeout=10):
        self.base_url = f"http://{host}"
        self.password = password
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Referer": self.base_url,
        })
        self._logged_in = False

    def login(self):
        """Authenticate with the switch."""
        # The SG108E uses a hashed password login
        # Try the common login endpoint
        url = f"{self.base_url}/logon.cgi"
        data = {
            "username": "admin",
            "password": hashlib.md5(self.password.encode()).hexdigest(),
            "cpassword": "",
            "logon": "Login",
        }
        resp = self.session.post(url, data=data, timeout=self.timeout)
        resp.raise_for_status()

        # Some firmware versions use a different login flow
        if "password" in resp.text.lower() and "error" in resp.text.lower():
            # Try plaintext password
            data["password"] = self.password
            resp = self.session.post(url, data=data, timeout=self.timeout)
            resp.raise_for_status()

        self._logged_in = True
        print(f"  Logged in to {self.base_url}")

    def logout(self):
        """End the management session."""
        if self._logged_in:
            try:
                self.session.get(
                    f"{self.base_url}/logout.cgi", timeout=self.timeout
                )
            except Exception:
                pass
            self._logged_in = False

    def _require_login(self):
        if not self._logged_in:
            raise RuntimeError("Not logged in. Call login() first.")

    def enable_8021q_vlans(self):
        """Enable 802.1Q VLAN mode on the switch."""
        self._require_login()
        url = f"{self.base_url}/vlan_8021q_config.cgi"
        data = {"status": "1", "apply": "Apply"}
        resp = self.session.post(url, data=data, timeout=self.timeout)
        resp.raise_for_status()
        print("  Enabled 802.1Q VLAN mode")

    def create_vlan(self, vlan_id, name, tagged_ports, untagged_ports):
        """
        Create or update a VLAN with specified port membership.

        Args:
            vlan_id: VLAN ID (1-4094)
            name: VLAN name string
            tagged_ports: list of 1-indexed port numbers to tag
            untagged_ports: list of 1-indexed port numbers to untag
        """
        self._require_login()

        # Build port membership bitmasks
        # The switch API uses a bitmask string or per-port fields
        url = f"{self.base_url}/vlan_8021q_add.cgi"

        data = {
            "vid": str(vlan_id),
            "vname": name,
        }

        # Set each port's membership: 0=not member, 1=untagged, 2=tagged
        for port in range(1, self.NUM_PORTS + 1):
            if port in untagged_ports:
                data[f"port{port}"] = "1"
            elif port in tagged_ports:
                data[f"port{port}"] = "2"
            else:
                data[f"port{port}"] = "0"

        data["apply"] = "Apply"

        resp = self.session.post(url, data=data, timeout=self.timeout)
        resp.raise_for_status()

        tagged_str = ",".join(str(p) for p in tagged_ports) or "none"
        untagged_str = ",".join(str(p) for p in untagged_ports) or "none"
        print(
            f"  VLAN {vlan_id} ({name}): "
            f"untagged=[{untagged_str}] tagged=[{tagged_str}]"
        )

    def delete_vlan(self, vlan_id):
        """Delete a VLAN. Cannot delete VLAN 1."""
        self._require_login()
        if vlan_id == 1:
            print("  Skipping delete of VLAN 1 (default)")
            return

        url = f"{self.base_url}/vlan_8021q_del.cgi"
        data = {"vid": str(vlan_id), "apply": "Apply"}
        try:
            resp = self.session.post(url, data=data, timeout=self.timeout)
            resp.raise_for_status()
        except Exception:
            pass  # VLAN may not exist yet

    def set_pvids(self, pvid_map):
        """
        Set the PVID (native VLAN) for each port.

        Args:
            pvid_map: dict mapping 1-indexed port number to VLAN ID
        """
        self._require_login()
        url = f"{self.base_url}/vlan_8021q_pvid.cgi"

        data = {}
        for port in range(1, self.NUM_PORTS + 1):
            pvid = pvid_map.get(port, 1)
            data[f"pvid{port}"] = str(pvid)
        data["apply"] = "Apply"

        resp = self.session.post(url, data=data, timeout=self.timeout)
        resp.raise_for_status()

        for port, pvid in sorted(pvid_map.items()):
            print(f"  Port {port} PVID -> {pvid}")

    def save_config(self):
        """Save the running configuration to flash."""
        self._require_login()
        url = f"{self.base_url}/save_config.cgi"
        data = {"apply": "Apply"}
        resp = self.session.post(url, data=data, timeout=self.timeout)
        resp.raise_for_status()
        print("  Configuration saved to flash")

    def apply_profile(self, profile):
        """
        Apply a complete VLAN profile to the switch.

        Args:
            profile: dict with keys:
                "vlans": list of dicts with keys:
                    "id", "name", "tagged", "untagged"
                "pvids": dict mapping port number to VLAN ID
        """
        self.login()
        try:
            print("Enabling 802.1Q VLANs...")
            self.enable_8021q_vlans()

            print("Creating VLANs...")
            for vlan in profile["vlans"]:
                self.create_vlan(
                    vlan_id=vlan["id"],
                    name=vlan["name"],
                    tagged_ports=vlan["tagged"],
                    untagged_ports=vlan["untagged"],
                )

            print("Setting PVIDs...")
            self.set_pvids(profile["pvids"])

            print("Saving configuration...")
            self.save_config()
        finally:
            self.logout()
