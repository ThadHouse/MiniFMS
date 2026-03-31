# Switch configuration profiles for MiniFMS
#
# Each profile defines:
#   vlans: list of VLAN definitions with port membership
#   pvids: port PVID (native/untagged VLAN) assignments
#
# Port membership types:
#   tagged   = port carries VLAN traffic with 802.1Q tag (trunk)
#   untagged = port strips VLAN tag (access port)

TRUNK_PORTS = [7, 8]

# ============================================================
# Profile: robot_a
# Switch 1 - Robot VLANs 10-40, LAN, WAN
#
# Port 1: VLAN 10  (Robot)
# Port 2: VLAN 20  (Robot)
# Port 3: VLAN 30  (Robot)
# Port 4: VLAN 40  (Robot)
# Port 5: VLAN 100 (LAN)
# Port 6: VLAN 150 (WAN)
# Port 7: Trunk
# Port 8: Trunk
# ============================================================
PROFILE_ROBOT_A = {
    "vlans": [
        {
            "id": 1,
            "name": "Default",
            "tagged": [],
            "untagged": [],  # Remove all ports from default VLAN
        },
        {
            "id": 10,
            "name": "Robot10",
            "tagged": TRUNK_PORTS,
            "untagged": [1],
        },
        {
            "id": 20,
            "name": "Robot20",
            "tagged": TRUNK_PORTS,
            "untagged": [2],
        },
        {
            "id": 30,
            "name": "Robot30",
            "tagged": TRUNK_PORTS,
            "untagged": [3],
        },
        {
            "id": 40,
            "name": "Robot40",
            "tagged": TRUNK_PORTS,
            "untagged": [4],
        },
        {
            "id": 100,
            "name": "LAN",
            "tagged": TRUNK_PORTS,
            "untagged": [5],
        },
        {
            "id": 150,
            "name": "WAN",
            "tagged": TRUNK_PORTS,
            "untagged": [6],
        },
    ],
    "pvids": {
        1: 10,
        2: 20,
        3: 30,
        4: 40,
        5: 100,
        6: 150,
        7: 1,
        8: 1,
    },
}

# ============================================================
# Profile: robot_b
# Switch 2 - Robot VLANs 50-80, LAN
#
# Port 1:   VLAN 50  (Robot)
# Port 2:   VLAN 60  (Robot)
# Port 3:   VLAN 70  (Robot, future)
# Port 4:   VLAN 80  (Robot, future)
# Port 5-6: VLAN 100 (LAN)
# Port 7-8: Trunk
# ============================================================
PROFILE_ROBOT_B = {
    "vlans": [
        {
            "id": 1,
            "name": "Default",
            "tagged": [],
            "untagged": [],
        },
        {
            "id": 50,
            "name": "Robot50",
            "tagged": TRUNK_PORTS,
            "untagged": [1],
        },
        {
            "id": 60,
            "name": "Robot60",
            "tagged": TRUNK_PORTS,
            "untagged": [2],
        },
        {
            "id": 70,
            "name": "Robot70",
            "tagged": TRUNK_PORTS,
            "untagged": [3],
        },
        {
            "id": 80,
            "name": "Robot80",
            "tagged": TRUNK_PORTS,
            "untagged": [4],
        },
        {
            "id": 100,
            "name": "LAN",
            "tagged": TRUNK_PORTS,
            "untagged": [5, 6],
        },
    ],
    "pvids": {
        1: 50,
        2: 60,
        3: 70,
        4: 80,
        5: 100,
        6: 100,
        7: 1,
        8: 1,
    },
}

# ============================================================
# Profile: lan
# Switch 3 - LAN only
#
# Port 1-6: VLAN 100 (LAN)
# Port 7-8: Trunk
# ============================================================
PROFILE_LAN = {
    "vlans": [
        {
            "id": 1,
            "name": "Default",
            "tagged": [],
            "untagged": [],
        },
        {
            "id": 100,
            "name": "LAN",
            "tagged": TRUNK_PORTS,
            "untagged": [1, 2, 3, 4, 5, 6],
        },
    ],
    "pvids": {
        1: 100,
        2: 100,
        3: 100,
        4: 100,
        5: 100,
        6: 100,
        7: 1,
        8: 1,
    },
}

# Static IP assignments for each switch (on VLAN 100 / LAN)
SWITCH_IPS = {
    "robot_a": "10.0.100.10",
    "robot_b": "10.0.100.11",
    "lan": "10.0.100.12",
}

PROFILES = {
    "robot_a": PROFILE_ROBOT_A,
    "robot_b": PROFILE_ROBOT_B,
    "lan": PROFILE_LAN,
}
