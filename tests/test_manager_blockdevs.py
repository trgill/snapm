# Copyright (C) 2023 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>
#
# tests/test_plugin.py - Plugin core unit tests
#
# This file is part of the snapm project.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions
# of the GNU General Public License v.2.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
import snapm
import snapm.manager.plugins as plugins
import snapm.manager.plugins.lvm2 as lvm2
import snapm.manager as manager
import snapm.command as command
import unittest
import logging

from ._util import LvmLoopBacked

SNAPSET_NAME = "testset0"

log = logging.getLogger()
log.level = logging.DEBUG
log.addHandler(logging.FileHandler("test.log"))

# 1GiB
_TEST_LOOPBACK_SIZE = 1024**3
_TEST_SOURCE_COUNT = 4


class ManagerBlockdevTests(unittest.TestCase):
    volumes = ["root", "home", "var", "data_vol"]
    thin_volumes = ["opt", "srv", "thin-vol"]

    def setUp(self):

        def cleanup_lvm():
            if hasattr(self, "_lvm"):
                self._lvm.destroy()

        self.addCleanup(cleanup_lvm)

        self._lvm = LvmLoopBacked(self.volumes, thin_volumes=self.thin_volumes)
        self._manager = manager.Manager()

    def test_blockdevs_create(self):
        snapset = self._manager.create_snapshot_set(
            SNAPSET_NAME, self._lvm.block_devs())
        command.print_snapsets(self._manager)
        self._manager.delete_snapshot_sets(snapm.Selection(name=SNAPSET_NAME))

    def test_find_snapshot_sets_one(self):
        self._manager.create_snapshot_set(SNAPSET_NAME, self._lvm.block_devs())
        sets = self._manager.find_snapshot_sets()
        self.assertEqual(len(sets), 1)
        self._manager.delete_snapshot_sets(snapm.Selection(name=SNAPSET_NAME))
