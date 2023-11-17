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
import unittest
import logging

log = logging.getLogger()
log.level = logging.DEBUG
log.addHandler(logging.FileHandler("test.log"))

import snapm.manager.plugins as plugins


class PluginTests(unittest.TestCase):
    """Test plugin helper functions"""

    def test_parse_snapshot_name(self):
        snapshot_names = {
            "root-snapset_backup_1693921253_-": ("backup", 1693921253, "/"),
            "data-snapset_backup_1693921253_-data": (
                "backup",
                1693921253,
                "/data",
            ),
            "home-snapset_myset_1693921266_-home": (
                "myset",
                1693921266,
                "/home",
            ),
            "srv-snapset_newset_1694704292_-srv": ("newset", 1694704292, "/srv"),
        }
        for snapshot_name in snapshot_names.keys():
            (origin, _) = snapshot_name.split("-", maxsplit=1)
            self.assertEqual(
                plugins.parse_snapshot_name(snapshot_name, origin),
                snapshot_names[snapshot_name],
            )

    def test_encode_mount_point(self):
        mounts = {
            "/": "-",
            "/home": "-home",
            "/var": "-var",
            "/opt": "-opt",
            "/var/tmp": "-var-tmp",
            "/var/foo-bar": "-var-foo--bar",
            "/foo_bar": "-foo_bar",
        }
        for mount in mounts.keys():
            self.assertEqual(plugins.encode_mount_point(mount), mounts[mount])

    def test_decode_mount_point(self):
        enc_mounts = {
            "-": "/",
            "-home": "/home",
            "-var": "/var",
            "-opt": "/opt",
            "-var-tmp": "/var/tmp",
            "-var-foo--bar": "/var/foo-bar",
            "-foo_bar": "/foo_bar",
        }
        for enc_mount in enc_mounts.keys():
            self.assertEqual(
                plugins.decode_mount_point(enc_mount), enc_mounts[enc_mount]
            )

    def test_format_snapshot_name(self):
        snapshot_parts = {
            (
                "data",
                "backup",
                1693921253,
                "/data",
            ): "data-snapset_backup_1693921253_-data",
            (
                "home",
                "myset",
                1693921266,
                "/home",
            ): "home-snapset_myset_1693921266_-home",
            (
                "srv",
                "newset",
                1694704292,
                "/srv",
            ): "srv-snapset_newset_1694704292_-srv",
        }
        for parts in snapshot_parts.keys():
            mount = plugins.encode_mount_point(parts[3])
            self.assertEqual(
                plugins.format_snapshot_name(parts[0], parts[1], parts[2], mount),
                snapshot_parts[parts],
            )

    def test__parse_proc_mounts_line(self):
        from snapm.manager.plugins._plugin import _parse_proc_mounts_line

        lines = {
            "/dev/mapper/fedora-root / xfs rw": (
                "/dev/mapper/fedora-root",
                "/",
            ),
            "/dev/mapper/fedora-data /data xfs rw": (
                "/dev/mapper/fedora-data",
                "/data",
            ),
            "/dev/vda2 /boot xfs rw": ("/dev/vda2", "/boot"),
        }
        for line in lines:
            self.assertEqual(_parse_proc_mounts_line(line), lines[line])
