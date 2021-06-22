"""
Machine ops is the swiss army knife of operational functions required
to perform server related configuration changes, be it network stack,
systemd changes or maybe a node reboot itself.
"""
import time
import os
from common.ops.abstract_ops import AbstractOps


class MachineOps(AbstractOps):
    """
    MachineOps class provides methods for
    handling the machine specific operations.
    """

    def reboot_nodes(self, nodes: list):
        """
        To reboot a given set of node(s)
        Arg:
            node(s) (str/list)
        Returns:
            None
        """
        if not isinstance(nodes, list):
            nodes = [nodes]

        for node in nodes:
            self.reboot_node(node)
            self.wait_node_power_down(node)

    def check_node_power_status(self, nodes: list) -> dict:
        """
        To check the node's power status. Simply to check if
        it is online or offline.
        Arg:
            node(s) (str/list)
        Returns:
            dict containing following key-value pairs,
                -> node (str) : state (True/False)
            herein True implies node being online and False, offline.
        """
        if not isinstance(nodes, list):
            nodes = [nodes]

        ret = {}
        for node in nodes:
            cmd = (f"ping -c1 -W1 -q {node} &>/dev/null")
            ret_val = int(os.system(cmd))
            self.logger.info(f"Ping command {cmd} : {ret_val}")
            if ret_val != 0:
                ret[node] = False
            else:
                ret[node] = True
        self.logger.info(f"{nodes} power state : {ret}")
        return ret

    def are_nodes_online(self, nodes: str):
        """
        Checks if all the nodes are online.

        Args:
            nodes (str|list): List of nodes
        Return:
        True if all the nodes are online else False
        """
        ret = self.check_node_power_status(nodes)
        for key in ret:
            if not ret[key]:
                return False
        return True

    def wait_node_power_up(self, node: str, timeout: int = 100):
        """
        Wait for a node to come up online.
        Arg:
            node (str)
        Returns:
            bool value: True if node is online or False.
        """
        status = self.check_node_power_status(node)
        if status[node]:
            self.logger.info(f"{node} online.")
            return True
        iter_v = 0
        while iter_v < timeout:
            status = self.check_node_power_status(node)
            if status[node]:
                self.logger.info(f"{node} online.")
                return True
            time.sleep(1)
            iter_v += 1
        status = self.check_node_power_status(node)
        if status[node]:
            self.logger.info(f"{node} online.")
            return True
        self.logger.error(f"{node} still offline.")
        return False

    def wait_node_power_down(self, node: str, timeout: int = 100):
        """
        Wait for a node to come down offline.
        Arg:
            node (str)
        Returns:
            bool value: True if node is online or False.
        """
        status = self.check_node_power_status(node)
        if not status[node]:
            self.logger.info(f"{node} offline.")
            return True
        iter_v = 0
        while iter_v < timeout:
            status = self.check_node_power_status(node)
            if not status[node]:
                self.logger.info(f"{node} offline.")
                return True
            time.sleep(1)
            iter_v += 1
        status = self.check_node_power_status(node)
        if not status[node]:
            self.logger.info(f"{node} offline.")
            return True
        self.logger.error(f"{node} still online.")
        return False

    def hard_terminate(self, server_list: list, client_list: list,
                       brick_root: dict):
        """
        hard terminate is inconsiderate. It will clear out the env
        completely and is to be used with caution. Don't use it inside the
        non disruptive tests or else, you might have a string of failures.
        Args:
            server_list (list): List of gluster server machines
            client_list (list): List of gluster client machines
            brick_root (dict): Dictionary of brick roots and nodes.
        """
        # Wait for nodes to power up.
        for server in server_list:
            self.wait_node_power_up(server)

        # Stop glusterd on the servers.
        self.stop_glusterd(server_list)

        # Wait for glusterd to stop.
        if not self.wait_for_glusterd_to_stop(server_list):
            raise Exception("Sheer panic! As hard terminate fails to stop"
                            "glusterd!")

        # Kill glusterfs and glusterfsd processes in the server machines.
        # TODO. Add other gluster related processes later.
        cmd = "pkill glusterfs; pkill glusterfsd"
        for node in server_list:
            self.execute_abstract_op_node(cmd, node, False)

        # Also need to kill the fuse process in the clients
        cmd = "pkill glusterfs"
        for node in client_list:
            self.execute_abstract_op_node(cmd, node, False)

        # Clear out the vol and peer file on the servers.
        cmd = ("rm -rf /var/lib/glusterd/vols/*; rm -rf /var/lib/glusterd"
               "/peers/*")
        for node in server_list:
            self.execute_abstract_op_node(cmd, node, False)

        # Clear out the brick dirs under the brick roots.
        for (server, brick) in brick_root.items():
            cmd = (f"rm -rf {brick}/*")
            self.execute_abstract_op_node(cmd, server, False)

        # Clear out the mountpoints in clients.
        cmd = "umount /mnt/*; rm -rf /mnt/*"
        for node in client_list:
            self.execute_abstract_op_node(cmd, node, False)

        # Flush the IP tables
        cmd = "iptables --flush"
        for node in server_list:
            self.execute_abstract_op_node(cmd, node, False)

    def check_os(self, os_name: str, os_version: str, nodes: str):
        """
        Checks the os release and compares the
        os and version.

        Args:
            os_name (str): Operating system name
            os_version (str): Operating system version
            nodes (str|list): Nodes on which command
                              has to be executed

        Returns: bool, True, if os_name and os_version found
                 else False
        """
        cmd = "cat /etc/os-release"
        os_name = os_name.lower()

        ret = self.execute_abstract_op_multinode(cmd,
                                                 nodes,
                                                 False)
        for item in ret:
            if item['error_code'] != 0:
                self.logger.error("Couldn't fetch the os-release"
                                  f" from {item['node']}")
                return False

            out = item['msg']
            if (
                os_name not in out[0].lower()
                or os_version not in out[1]
            ):
                return False

        return True

    def bring_down_network_interface(self, node: str,
                                     timeout: int = 150):
        """Brings the network interface down for a defined time

            Args:
                node (str): Node at which the interface has to be bought down
                timeout (int): Time duration (in secs) for which network has to
                               be down

            Returns:
                network_status(object): Returns a process object
        """
        int_cmd = "ps -aux | grep glusterd"
        ret = self.execute_abstract_op_node(int_cmd,
                                            node, False)
        pid = None
        for i in ret['msg'][0].split(' '):
            if i.isnumeric():
                pid = i
                break

        int_cmd = f"cat /proc/{pid}/net/route"
        ret = self.execute_abstract_op_node(int_cmd,
                                            node, False)
        if ret['error_code'] != 0:
            raise Exception("Failed: Could not find the interface")

        interface = ret['msg'][1].split('\t')[0]

        cmd = (f"ip link set {interface} down\nsleep {timeout}\n"
               f"ip link set {interface} up")
        cmd1 = f"echo  \"{cmd}\"> 'test.sh'"
        self.execute_abstract_op_node(cmd1, node)
        network_status = self.execute_command_async("sh test.sh", node)
        return network_status

    def reload_glusterd_service(self, node):
        """Reload the Daemons when unit files are changed.

        Args:
            node (str): Node on which daemon has to be reloaded.

        Returns:
            bool: True, On successful daemon reload
                False, Otherwise
        """
        if self.check_os('rhel', '6', [node]):
            cmd = 'service glusterd reload'
            ret = self.execute_abstract_op_node(node, cmd, False)
        else:
            cmd = "systemctl daemon-reload"
            ret = self.execute_abstract_op_node(cmd, node, False)

        if ret['error_code'] != 0:
            self.logger.error("Failed to reload the daemon")
            return False
        return True
