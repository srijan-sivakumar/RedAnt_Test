"""
Copyright (C) 2016-2017  Red Hat, Inc. <http://www.redhat.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

Description:
This test case tests various add brick scenarios
"""
import random
from tests.d_parent_test import DParentTest

# disruptive;dist-rep


class TestCase(DParentTest):

    def run_test(self, redant):
        """
        1. Setup a volume
        2. Create a 4*replica_count brick list
        3. Add a single brick to the volume, 
           which should fail
        4. Add a non-existing brick, which should
           fail.
        5. Add a brick from a node which is not a
           part of the cluster.
        """
        # form bricks list to test add brick functionality
        rep_count = self.vol_type_inf[self.conv_dict['rep']]
        rep_count = rep_count['replica_count']
        print(rep_count)
        num_of_bricks = 4 * rep_count
        print(num_of_bricks)

        _, self.bricks_list = redant.form_brick_cmd(self.server_list,
                                                 self.brick_roots,
                                                 self.vol_name,
                                                 num_of_bricks)
        self.bricks_list = self.bricks_list.split(' ')
        print("\n",self.bricks_list)
        if self.bricks_list is None:
            raise Exception("Bricks list is empty")
        
        # Try to add a single brick to volume, which should fail as it is a
        # replicated volume, we should pass multiple of replica count number
        # of bricks
        try:
            redant.add_brick(self.vol_name,
                             self.bricks_list[0],
                             self.server_list[0])
        except Exception as error:
            print("\n1. ",error)

        # add brick replica count number of bricks in which one is a
        # non existing brick (not using the brick used in the earlier test)
        print(f"Replica count: {rep_count}\n")
        bricks_to_add = self.bricks_list[1:rep_count + 1]
        # make one of the bricks a non-existing one (randomly)
        random_index = random.randint(0, rep_count - 1)
        bricks_to_add[random_index] += "/non_existing_brick"

        br_cmd = " ".join(bricks_to_add)
        print(f"\nBrick cmd:\n{br_cmd}\n")
        try:
            redant.add_brick(self.vol_name,
                            br_cmd, self.server_list[0],
                            replica_count=rep_count)
        except Exception as error:
            print(f"\n2. {error}\n")

        # # add a brick from a node which is not a part of the cluster
        # # (not using bricks used in earlier tests)
        # bricks_to_add = self.bricks_list[rep_count + 1:
        #                                  (2 * rep_count) + 1]
        # # change one (random) brick's node name to a non existent node
        # random_index = random.randint(0, rep_count - 1)
        # brick_to_change = bricks_to_add[random_index].split(":")
        # brick_to_change[0] = "abc.def.ghi.jkl"
        # bricks_to_add[random_index] = ":".join(brick_to_change)
        # self.assertNotEqual(
        #     add_brick(self.mnode, self.volname, bricks_to_add, **kwargs)[0], 0,
        #     "Expected: It should fail to add brick from a node which is not "
        #     "part of a cluster. Actual: Successfully added bricks from node "
        #     "which is not a part of cluster to volume")
        # g.log.info("Failed to add bricks from node which is not a part of "
        #            "cluster to volume (as expected)")

        # # add correct number of valid bricks, it should succeed
        # # (not using bricks used in earlier tests)
        # bricks_to_add = self.bricks_list[(2 * rep_count) + 1:
        #                                  (3 * rep_count) + 1]
        # self.assertEqual(
        #     add_brick(self.mnode, self.volname, bricks_to_add, **kwargs)[0], 0,
        #     "Failed to add the bricks to the volume")
        # g.log.info("Successfully added bricks to volume")

        # # Perform rebalance start operation
        # self.assertEqual(rebalance_start(self.mnode, self.volname)[0], 0,
        #                  "Rebalance start failed")