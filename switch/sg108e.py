"""
TP-Link TL-SG108E Easy Smart Switch configuration library.

Communicates with the switch via its HTTP management interface.
Tested against TL-SG108E V6 hardware, firmware 1.0.0 Build 20211209.

Key details about this switch's web API:
  - Login is the only POST endpoint; all config changes use GET.
  - The switch requires "Connection: close" — it cannot handle
    persistent/keep-alive connections.
  - No cookies are used; sessions are tracked by client IP.
  - VLAN port membership values: 0=untagged, 1=tagged, 2=not member.
  - PVIDs are set per-VLAN with a port bitmask, not per-port.
"""

import re
import time
import requests


class SG108E:
    """Interface to a TL-SG108E switch's web management API."""

    NUM_PORTS = 8

    def __init__(self, host, password="minifms", timeout=10):
        self.base_url = f"http://{host}"
        self.password = password
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Referer": self.base_url,
            "Connection": "close",
        })
        self._logged_in = False

    # -- Authentication ------------------------------------------------

    def setup_password(self):
        """Set the admin password on a factory-reset switch.

        The factory-reset login page (errType 6) accepts a POST to
        /logon.cgi with plaintext credentials and logon="Confirm".
        The switch may drop the connection afterwards as it restarts
        its web service.
        """
        url = f"{self.base_url}/logon.cgi"
        data = {
            "username": "admin",
            "password": self.password,
            "cpassword": self.password,
            "logon": "Confirm",
        }
        try:
            resp = self.session.post(url, data=data, timeout=self.timeout)
            resp.raise_for_status()
        except (requests.ConnectionError, requests.exceptions.RemoteDisconnected):
            pass  # expected — switch restarts its web service
        print(f"  Admin password configured on {self.base_url}")
        print("  Waiting for switch to be ready...")
        time.sleep(3)

    def login(self):
        """Authenticate with the switch (POST with plaintext password)."""
        url = f"{self.base_url}/logon.cgi"
        data = {
            "username": "admin",
            "password": self.password,
            "cpassword": "",
            "logon": "Login",
        }
        resp = self.session.post(url, data=data, timeout=self.timeout)
        resp.raise_for_status()
        self._logged_in = True
        print(f"  Logged in to {self.base_url}")

    def logout(self):
        """End the management session."""
        if self._logged_in:
            try:
                self.session.get(
                    f"{self.base_url}/Logout.htm", timeout=self.timeout
                )
            except Exception:
                pass
            self._logged_in = False

    def _require_login(self):
        if not self._logged_in:
            raise RuntimeError("Not logged in. Call login() first.")

    # -- VLAN configuration --------------------------------------------

    def enable_8021q_vlans(self):
        """Enable 802.1Q VLAN mode on the switch."""
        self._require_login()
        resp = self.session.get(
            f"{self.base_url}/qvlanSet.cgi",
            params={"qvlan_en": "1", "qvlan_mode": "Apply"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        print("  Enabled 802.1Q VLAN mode")

    def create_vlan(self, vlan_id, name, tagged_ports, untagged_ports):
        """
        Create or update a VLAN with specified port membership.

        Port membership values for this firmware:
            0 = untagged (access)
            1 = tagged   (trunk)
            2 = not member
        """
        self._require_login()

        params = {
            "vid": str(vlan_id),
            "vname": name,
        }
        for port in range(1, self.NUM_PORTS + 1):
            if port in untagged_ports:
                params[f"selType_{port}"] = "0"
            elif port in tagged_ports:
                params[f"selType_{port}"] = "1"
            else:
                params[f"selType_{port}"] = "2"
        params["qvlan_add"] = "Add/Modify"

        resp = self.session.get(
            f"{self.base_url}/qvlanSet.cgi",
            params=params,
            timeout=self.timeout,
        )
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
        try:
            resp = self.session.get(
                f"{self.base_url}/qvlanSet.cgi",
                params={"selVlans": str(vlan_id), "qvlan_del": "Delete"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except Exception:
            pass  # VLAN may not exist yet

    def set_pvids(self, pvid_map):
        """
        Set the PVID (native VLAN) for each port.

        The switch API sets PVIDs per-VLAN with a port bitmask:
            GET /vlanPvidSet.cgi?pbm=<bitmask>&pvid=<vlan_id>
        So we group ports by their target PVID and make one request
        per unique PVID value.
        """
        self._require_login()

        # Group ports by PVID
        pvid_to_ports = {}
        for port in range(1, self.NUM_PORTS + 1):
            pvid = pvid_map.get(port, 1)
            pvid_to_ports.setdefault(pvid, []).append(port)

        for pvid, ports in sorted(pvid_to_ports.items()):
            # Build bitmask: port 1 = bit 0, port 2 = bit 1, etc.
            bitmask = 0
            for p in ports:
                bitmask |= 1 << (p - 1)

            resp = self.session.get(
                f"{self.base_url}/vlanPvidSet.cgi",
                params={"pbm": str(bitmask), "pvid": str(pvid)},
                timeout=self.timeout,
            )
            resp.raise_for_status()

            port_str = ",".join(str(p) for p in ports)
            print(f"  Ports [{port_str}] PVID -> {pvid}")

    # -- System --------------------------------------------------------

    def save_config(self):
        """Save the running configuration to flash."""
        self._require_login()
        resp = self.session.post(
            f"{self.base_url}/savingconfig.cgi",
            data={"action_op": "save"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        print("  Configuration saved to flash")

    def set_ip(self, ip_addr, netmask="255.255.255.0", gateway="10.0.100.1"):
        """
        Change the switch's management IP address.

        Note: after this call the switch will be reachable at the new IP.
        """
        self._require_login()
        resp = self.session.get(
            f"{self.base_url}/ip_setting.cgi",
            params={
                "dhcpSetting": "disable",
                "ip_address": ip_addr,
                "ip_netmask": netmask,
                "ip_gateway": gateway,
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        print(f"  IP set to {ip_addr} (mask {netmask}, gw {gateway})")

    # -- High-level ----------------------------------------------------

    def apply_profile(self, profile, new_ip=None):
        """
        Apply a complete VLAN profile to the switch.

        Args:
            profile: dict with "vlans" and "pvids" keys
            new_ip: optional new management IP address to assign
        """
        print("Setting up admin password...")
        self.setup_password()

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

            if new_ip:
                print("Setting switch IP address...")
                self.set_ip(new_ip)

            print("Saving configuration...")
            self.save_config()
        finally:
            self.logout()
