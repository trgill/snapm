# Copyright (C) 2023 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>
#
# tests/test_manager.py - Plugin core unit tests
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

import snapm

from tests import MockArgs

log = logging.getLogger()
log.level = logging.DEBUG
log.addHandler(logging.FileHandler("test.log"))


class SnapmTests(unittest.TestCase):
    """Test snapm module"""

    def test_set_debug_mask(self):
        snapm.set_debug_mask(snapm.SNAPM_DEBUG_ALL)

    def test_set_debug_mask_bad_mask(self):
        with self.assertRaises(ValueError) as cm:
            snapm.set_debug_mask(snapm.SNAPM_DEBUG_ALL + 1)

    def test_SnapmLogger(self):
        sl = snapm.SnapmLogger("snapm", 0)
        sl.debug("debug")

    def test_SnapmLogger_set_debug_mask(self):
        sl = snapm.SnapmLogger("snapm", 0)
        sl.set_debug_mask(snapm.SNAPM_DEBUG_ALL)

    def test_SnapmLogger_set_debug_mask_bad_mask(self):
        sl = snapm.SnapmLogger("snapm", 0)
        with self.assertRaises(ValueError) as cm:
            sl.set_debug_mask(snapm.SNAPM_DEBUG_ALL + 1)

    def test_SnapmLogger_debug_masked(self):
        sl = snapm.SnapmLogger("snapm", 0)
        snapm.set_debug_mask(snapm.SNAPM_DEBUG_ALL)
        sl.set_debug_mask(snapm.SNAPM_DEBUG_MANAGER)
        sl.debug_masked("quux")

    def test_Selection_is_null(self):
        s = snapm.Selection()
        self.assertTrue(s.is_null())

    def test_Selection_is_single_name(self):
        s = snapm.Selection(name="name")
        self.assertTrue(s.is_single())

    def test_Selection_is_single_uuid(self):
        s = snapm.Selection(uuid="2a6fd226-b400-577f-afe7-0c1a39c78488")
        self.assertTrue(s.is_single())

    def test_Selection_is_not_single(self):
        s = snapm.Selection(origin="fedora/root")
        self.assertFalse(s.is_single())

    def test_Selection_is_not_null(self):
        s = snapm.Selection(name="name")
        self.assertFalse(s.is_null())

    def test_Selection_from_cmd_args_identifier_name(self):
        cmd_args = MockArgs()
        cmd_args.identifier = "name"
        s = snapm.Selection.from_cmd_args(cmd_args)
        self.assertEqual(cmd_args.identifier, s.name)

    def test_Selection_from_cmd_args_identifier_uuid(self):
        cmd_args = MockArgs()
        cmd_args.identifier = "2a6fd226-b400-577f-afe7-0c1a39c78488"
        s = snapm.Selection.from_cmd_args(cmd_args)
        self.assertEqual(cmd_args.identifier, s.uuid)

    def test_Selection_from_cmd_args_name(self):
        cmd_args = MockArgs()
        cmd_args.name = "name"
        s = snapm.Selection.from_cmd_args(cmd_args)
        self.assertEqual(cmd_args.name, s.name)

    def test_Selection_from_cmd_args_uuid(self):
        cmd_args = MockArgs()
        cmd_args.uuid = "2a6fd226-b400-577f-afe7-0c1a39c78488"
        s = snapm.Selection.from_cmd_args(cmd_args)
        self.assertEqual(cmd_args.uuid, s.uuid)

    def test_Selection_from_cmd_args_bad_uuid(self):
        cmd_args = MockArgs()
        cmd_args.uuid = "not-a-uuid"
        with self.assertRaises(snapm.SnapmInvalidIdentifierError) as cm:
            s = snapm.Selection.from_cmd_args(cmd_args)

    def test_valid_selection_snapset(self):
        s = snapm.Selection(name="testset0", timestamp=1693921253)
        s.check_valid_selection(snapshot_set=True)

    def test_valid_selection_snapshot(self):
        s = snapm.Selection(origin="home", mount_point="/home")
        s.check_valid_selection(snapshot=True)

    def test_valid_selection_snapset_invalid(self):
        s = snapm.Selection(origin="home")
        with self.assertRaises(ValueError) as cm:
            s.check_valid_selection(snapshot_set=True)

    def test_valid_selection_snapshot_invalid(self):
        s = snapm.Selection(name="testset0")
        with self.assertRaises(ValueError) as cm:
            s.check_valid_selection(snapshot=True)
