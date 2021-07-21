"""
Copyright (C) 2016-2018  Red Hat, Inc. <http://www.redhat.com>

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
    Test Cases in this module tests the self heal daemon process.
@runs_on([['replicated', 'distributed-replicated'],
          ['glusterfs', 'cifs', 'nfs']])
"""
# disruptive;rep
# TODO: nfs, cifs

import time
from tests.d_parent_test import DParentTest


class TestCase(DParentTest):

    def run_test(self, redant):
        """
        Test Script which verifies that the existing glustershd should take
        care of self healing

        * Create and start the Replicate volume
        * Check the glustershd processes - Note the pids
        * Bring down the One brick ( lets say brick1)  without affecting
          the cluster
        * Create 1000 files on volume
        * bring the brick1 up which was killed in previous steps
        * check the heal info - proactive self healing should start
        * Bring down brick1 again
        * wait for 60 sec and brought up the brick1
        * Check the glustershd processes - pids should be different
        * Monitor the heal till its complete

        """
        self.all_mounts_procs = []
        self.mounts = redant.es.get_mnt_pts_dict_in_list(self.vol_name)
        # Verfiy glustershd process releases its parent process
        if not redant.is_shd_daemonized(self.server_list):
            raise Exception("Self Heal Daemon process was still"
                            " holding parent process.")

        # check the self-heal daemon process
        ret, glustershd_pids = (redant.
                                get_self_heal_daemon_pid(self.server_list))
        if not ret:
            raise Exception("Either No self heal daemon process found or "
                            "more than One self heal daemon process "
                            f"found : {glustershd_pids}")

        # select the bricks to bring offline
        bricks_to_bring_offline = \
            redant.select_volume_bricks_to_bring_offline(self.vol_name,
                                                         self.server_list[0])
        # Bring down the selected bricks
        redant.bring_bricks_offline(self.vol_name, bricks_to_bring_offline)
        if not redant.are_bricks_offline(self.vol_name,
                                         bricks_to_bring_offline,
                                         self.server_list[0]):
            raise Exception("Failed to bring down the bricks. Please "
                            "check the log file for more details.")

        # get the bricks which are running
        online_bricks = redant.get_online_bricks_list(self.vol_name,
                                                      self.server_list[0])

        # write 1MB files to the mounts
        cmd = ("for i in `seq 1 1000`; "
               f"do dd if=/dev/urandom of={self.mountpoint}/file_$i "
               "bs=1M count=1; done")
        proc = redant.execute_command_async(cmd, self.client_list[0])
        self.all_mounts_procs.append(proc)

        # Validate IO
        if not redant.validate_io_procs(self.all_mounts_procs,
                                        self.mounts):
            raise Exception("IO failed on some of the clients")

        # check the heal info
        heal_info = redant.get_heal_info_summary(self.server_list[0],
                                                 self.vol_name)
        if heal_info is None:
            raise Exception("Failed to get the heal info summary.")

        # Bring bricks online
        redant.bring_bricks_online(self.vol_name, self.server_list,
                                  bricks_to_bring_offline, True)
        if not redant.are_bricks_online(self.vol_name,
                                        bricks_to_bring_offline,
                                        self.server_list[0]):
            raise Exception("Failed to bring bricks: "
                            f"{bricks_to_bring_offline} online")

        # Wait for 90 sec to start self healing
        time.sleep(90)

        # check the heal info
        heal_info_after_brick_online = (redant.
                                        get_heal_info_summary(
                                            self.server_list[0],
                                            self.vol_name))
        if heal_info_after_brick_online is None:
            raise Exception("Failed to get the heal info summary.")

        # check heal pending is decreased
        flag = False
        for brick in online_bricks:
            if int(heal_info_after_brick_online[brick]['numberOfEntries'])\
                    < int(heal_info[brick]['numberOfEntries']):
                flag = True
                break

        if not flag:
            raise Exception("Pro-active self heal is not started")

        # # bring down bricks again
        # g.log.info("Going to bring down the brick process "
        #            "for %s", bricks_to_bring_offline)
        # ret = bring_bricks_offline(self.volname, bricks_to_bring_offline)
        # self.assertTrue(ret, ("Failed to bring down the bricks. Please "
        #                       "check the log file for more details."))
        # g.log.info("Brought down the brick process "
        #            "for %s successfully", bricks_to_bring_offline)

        # # wait for 60 sec and brought up the brick again
        # g.log.info('waiting for 60 sec and brought up the brick again')
        # time.sleep(60)
        # g.log.info("Bring bricks: %s online", bricks_to_bring_offline)
        # ret = bring_bricks_online(self.mnode, self.volname,
        #                           bricks_to_bring_offline, 'glusterd_restart')
        # self.assertTrue(ret, ("Failed to bring bricks: %s online"
        #                       % bricks_to_bring_offline))
        # g.log.info("Successfully brought all bricks: %s online",
        #            bricks_to_bring_offline)

        # # Verfiy glustershd process releases its parent process
        # ret = is_shd_daemonized(self.server_list)
        # self.assertTrue(ret, ("Either No self heal daemon process found or "
        #                       "more than One self heal daemon process found"))

        # # check the self-heal daemon process
        # ret, pids = get_self_heal_daemon_pid(self.server_list)
        # self.assertTrue(ret, ("Either No self heal daemon process found or "
        #                       "more than One self heal daemon process "
        #                       "found : %s" % pids))

        # shd_pids_after_bricks_online = pids

        # # compare the glustershd pids
        # self.assertNotEqual(glustershd_pids,
        #                     shd_pids_after_bricks_online,
        #                     ("self heal daemon process are same before and "
        #                      "after bringing up bricks online"))
        # g.log.info("EXPECTED : self heal daemon process are different before "
        #            "and after bringing up bricks online")

        # # wait for heal to complete
        # g.log.info("Monitoring the heal.....")
        # ret = monitor_heal_completion(self.mnode, self.volname)
        # self.assertTrue(ret, ("Heal is not completed on volume %s"
        #                       % self.volname))
        # g.log.info("Heal Completed on volume %s", self.volname)

        # # Check if heal is completed
        # ret = is_heal_complete(self.mnode, self.volname)
        # self.assertTrue(ret, 'Heal is not complete')
        # g.log.info('Heal is completed successfully')
