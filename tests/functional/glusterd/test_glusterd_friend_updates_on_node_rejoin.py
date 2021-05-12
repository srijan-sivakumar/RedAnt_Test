#  Copyright (C) 2021 Red Hat, Inc. <http://www.redhat.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with this program; if not, write to the Free Software Foundation, Inc.,
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from time import sleep
from datetime import datetime, timedelta
from tests.abstract_test import AbstractTest

# disruptive;


class TestGlusterdFriendUpdatesWhenPeerRejoins(AbstractTest):

    def run_test(self, redant):
        """
        Test Steps:
        1. Restart glusterd on one of the node
        2. Check friend updates happened between nodes where
           glusterd was running
        3. Check friend updates between rejoined node to each other node
        """
        # Restart glusterd on one of the node
        redant.restart_glusterd(self.server_list[0])

        redant.wait_for_glusterd_to_start(self.server_list[0])

        # Save the current UTC time
        # Reducing 1 second to adjust with the race conditions in logging
        curr_time = datetime.utcnow() - timedelta(seconds=1)
        curr_time = curr_time.strftime("%H:%M:%S")

        # Minimum cluster size
        min_clstr_sz = 2

        # Friend updates for a minimum cluster
        min_updt = 4

        # Current cluster size
        crnt_clstr_size = len(self.server_list)

        # Wait until all the updates between the cluster nodes finish
        sleep(2 * crnt_clstr_size)

        # Intentional, to leverage the filtering of command line
        cmd = "gluster peer status | grep 'Uuid:' | cut -d ':' -f 2"
        ret = redant.execute_command(cmd, self.server_list[0])
        peer_lst = ret['msg'][0].splitlines()
        peer_lst = [p_uuid.strip() for p_uuid in peer_lst]

        # Check if there are any friend update between other nodes
        # and the restarted node
        for server in self.server_list:
            # Don't check on the restarted node
            if server != self.server_list[0]:
                for uuid in peer_lst:
                    cmd = ("awk '/%s/,0' /var/log/glusterfs/glusterd.log |"
                           " grep '_handle_friend_update' | grep %s | wc -l"
                           % (curr_time, uuid))
                    ret = redant.execute_command(cmd, self.server_list[0])
                    if int(ret['msg'][0]) != 0:
                        raise Exception("Unexpected: Found friend updates"
                                        " between other nodes")

        redant.looger.info("Expected: No friend updates between other"
                           " peer nodes")

        # Check friend updates between rejoined node and other nodes
        cmd = ("awk '/%s/,0' /var/log/glusterfs/glusterd.log "
               "| grep '_handle_friend_update' | wc -l" % curr_time)
        ret = redant.execute_command(cmd, self.server_list[0])
        count = int(ret['msg'][0])

        # Calculate the expected friend updates for a given cluster size
        expected_frnd_updts = min_updt * (crnt_clstr_size - min_clstr_sz + 1)
        if count != expected_frnd_updts:
            raise Exception("Count of friend updates"
                            " is not equal to the expected value")
