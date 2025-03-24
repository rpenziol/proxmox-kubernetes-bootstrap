#!/usr/bin/env python3

from pathlib import Path
from typing import Dict, List
import http.client
import json
import re
import ssl


class PromoxHost:
    def __init__(self):
        ansible_vars_file = Path(Path(__file__).parent.parent, "group_vars", "all.yaml")

        with open(ansible_vars_file) as f:
            ansible_vars_content = f.read()

        self.ip = re.search("proxmox_ip_address: (.*)", ansible_vars_content)[1]
        self.username = re.search("proxmox_username: (.*)", ansible_vars_content)[1]
        self.password = re.search("proxmox_password: (.*)", ansible_vars_content)[1]
        self.ssh_port = re.search("proxmox_ssh_port: (.*)", ansible_vars_content)[1]
        self.https_port = re.search("proxmox_https_port: (.*)", ansible_vars_content)[1]
        self.trust_invalid_https_certs = re.search(
            "proxmox_trust_invalid_https_certs: (.*)", ansible_vars_content
        )[1]


class ProxmoxVM:
    def __init__(self, node: str, meta: Dict, network_interfaces: Dict):
        self.node = node
        self.meta = meta
        self.network_interfaces = network_interfaces

    @property
    def name(self):
        return self.meta["name"]

    @property
    def tags(self):
        tags = [tag.strip() for tag in self.meta["tags"].split(",")]
        return tags

    @property
    def ip(self):
        if not self.network_interfaces:
            return None

        for interface in self.network_interfaces:
            if interface["name"] == "lo":
                continue

            for ip in interface["ip-addresses"]:
                if ip["ip-address-type"] == "ipv6":
                    continue

                # Return first non-loopback ipv4 address
                return ip["ip-address"]

    @property
    def running(self):
        return self.meta["status"] == "running"


class ProxmoxAPI:
    def __init__(self, host: PromoxHost):
        self.host = host
        self.url = f"{host.ip}:{host.https_port}"
        self.auth_cookie = self.auth()

    def auth(self):
        conn = http.client.HTTPSConnection(
            self.url, context=ssl._create_unverified_context(), timeout=10
        )
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        conn.request(
            "POST",
            "/api2/json/access/ticket",
            f"username={self.host.username}&password={self.host.password}",
            headers,
        )

        res = conn.getresponse()
        data = res.read()
        return json.loads(data.decode("utf-8"))["data"]

    def get(self, url: str, data=None):
        conn = http.client.HTTPSConnection(
            self.url, context=ssl._create_unverified_context(), timeout=10
        )
        headers = {"Cookie": f"PVEAuthCookie={self.auth_cookie['ticket']}"}
        conn.request("GET", url, body=data, headers=headers)
        res = conn.getresponse()
        data = res.read()

        return json.loads(data.decode("utf-8"))["data"]

    def get_vms(self) -> List[ProxmoxVM]:
        vms = []

        for node in self.get("/api2/json/nodes"):
            node_vms = self.get(f"/api2/json/nodes/{node['node']}/qemu")

            for node_vm in node_vms:
                response = self.get(
                    f"/api2/json/nodes/{node['node']}/qemu/{node_vm['vmid']}/agent/network-get-interfaces"
                )
                # Return 'None' in case VM isn't running
                network_interfaces = response["result"] if response else None

                vm = ProxmoxVM(node["node"], node_vm, network_interfaces)
                vms.append(vm)

        return vms


if __name__ == "__main__":
    proxmox = PromoxHost()

    inventory = {
        "_meta": {
            "hostvars": {
                "proxmox": {
                    "ansible_host": proxmox.ip,
                    "ansible_port": proxmox.ssh_port,
                }
            }
        },
        "all": {"hosts": ["proxmox"], "children": []},
    }

    for vm in ProxmoxAPI(proxmox).get_vms():
        if not vm.running or not vm.ip:
            continue

        inventory["_meta"]["hostvars"][vm.name] = {"ansible_host": vm.ip}

        for tag in vm.tags:
            if tag not in inventory.keys():
                inventory["all"]["children"].append(tag)
                inventory[tag] = {"hosts": [vm.name]}
            else:
                inventory[tag]["hosts"].append(vm.name)

    print((json.dumps(inventory, indent=True)))
