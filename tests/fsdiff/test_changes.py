# Copyright Red Hat
#
# tests/fsdiff/test_changes.py - ChangeDetector tests.
#
# This file is part of the snapm project.
#
# SPDX-License-Identifier: Apache-2.0
import unittest

from snapm.fsdiff.changes import ChangeDetector, ChangeType, FileChange
from snapm.fsdiff.options import DiffOptions

from ._util import make_entry

class TestChangeDetector(unittest.TestCase):
    def setUp(self):
        self.detector = ChangeDetector()
        self.opts = DiffOptions()

    def test_changes__str__(self):
        change = FileChange(ChangeType.CONTENT, "h1", "h2", "desc")
        self.assertIn("change_type: content", str(change))
        self.assertIn("old_value: h1", str(change))

    def test_no_changes(self):
        entry_a = make_entry("/a", content_hash="hash1")
        entry_b = make_entry("/a", content_hash="hash1")
        changes = self.detector.detect_changes(entry_a, entry_b, self.opts)
        self.assertEqual(len(changes), 0)

    def test_content_change(self):
        entry_a = make_entry("/a", content_hash="hash1")
        entry_b = make_entry("/a", content_hash="hash2")
        changes = self.detector.detect_changes(entry_a, entry_b, self.opts)

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].change_type, ChangeType.CONTENT)
        self.assertEqual(changes[0].old_value, "hash1")
        self.assertEqual(changes[0].new_value, "hash2")

    def test_metadata_perms_change(self):
        entry_a = make_entry("/a", mode=0o100644)
        entry_b = make_entry("/a", mode=0o100755)
        changes = self.detector.detect_changes(entry_a, entry_b, self.opts)

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].change_type, ChangeType.PERMISSIONS)

    def test_metadata_ownership_change(self):
        entry_a = make_entry("/a", uid=1000)
        entry_b = make_entry("/a", uid=1001)
        changes = self.detector.detect_changes(entry_a, entry_b, self.opts)

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].change_type, ChangeType.OWNERSHIP)

    def test_symlink_target_change(self):
        # _util.make_entry defaults target to "/target/path"
        entry_a = make_entry("/link", is_symlink=True)
        entry_b = make_entry("/link", is_symlink=True)
        # Manually change one target
        entry_b.symlink_target = "/new/target"

        changes = self.detector.detect_changes(entry_a, entry_b, self.opts)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].change_type, ChangeType.SYMLINK_TARGET)
        self.assertEqual(changes[0].new_value, "/new/target")

    def test_xattr_change(self):
        entry_a = make_entry("/file")
        entry_b = make_entry("/file")
        # Manually add xattrs (make_entry doesn't support them via args)
        entry_a.xattrs = {"security.selinux": "unconfined_u:object_r:user_home_t:s0"}
        entry_b.xattrs = {"security.selinux": "system_u:object_r:user_home_t:s0"}

        changes = self.detector.detect_changes(entry_a, entry_b, self.opts)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].change_type, ChangeType.XATTRS)

    def test_options_ignore_timestamps(self):
        entry_a = make_entry("/a", mtime=1000)
        entry_b = make_entry("/a", mtime=2000)

        # Should detect without ignore flag
        changes = self.detector.detect_changes(entry_a, entry_b, self.opts)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].change_type, ChangeType.TIMESTAMPS)

        # Should NOT detect with ignore flag
        self.opts.ignore_timestamps = True
        changes = self.detector.detect_changes(entry_a, entry_b, self.opts)
        self.assertEqual(len(changes), 0)

    def test_options_ignore_permissions(self):
        entry_a = make_entry("/a", mtime=1000, mode=0o600)
        entry_b = make_entry("/a", mtime=1000, mode=0o700)

        # Should detect without ignore flag
        changes = self.detector.detect_changes(entry_a, entry_b, self.opts)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].change_type, ChangeType.PERMISSIONS)

        # Should NOT detect with ignore flag
        self.opts.ignore_permissions = True
        changes = self.detector.detect_changes(entry_a, entry_b, self.opts)
        self.assertEqual(len(changes), 0)

    def test_options_ignore_ownership(self):
        entry_a = make_entry("/a", mtime=1000, mode=0o600, uid=1000)
        entry_b = make_entry("/a", mtime=1000, mode=0o600, uid=1001)

        # Should detect without ignore flag
        changes = self.detector.detect_changes(entry_a, entry_b, self.opts)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].change_type, ChangeType.OWNERSHIP)

        # Should NOT detect with ignore flag
        self.opts.ignore_ownership = True
        changes = self.detector.detect_changes(entry_a, entry_b, self.opts)
        self.assertEqual(len(changes), 0)

    def test_options_content_only(self):
        self.opts.content_only = True
        # Create entries diff permissions AND diff content
        entry_a = make_entry("/a", mode=0o644, content_hash="h1")
        entry_b = make_entry("/a", mode=0o777, content_hash="h2")
        changes = self.detector.detect_changes(entry_a, entry_b, self.opts)

        # Should catch content, ignore permissions
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].change_type, ChangeType.CONTENT)

    def test_detect_added(self):
        """Test changes detected for added files."""
        entry = make_entry("/new", content_hash="h1", mode=0o755, uid=1000)
        # Add symlink and xattrs to cover all branches
        entry.xattrs = {"user.test": b"val"}

        changes = self.detector.detect_added(entry, self.opts)

        types = {c.change_type for c in changes}
        self.assertIn(ChangeType.CONTENT, types)
        self.assertIn(ChangeType.PERMISSIONS, types)
        self.assertIn(ChangeType.OWNERSHIP, types)
        self.assertIn(ChangeType.TIMESTAMPS, types)
        self.assertIn(ChangeType.XATTRS, types)

        # Verify specific logic
        perm_change = next(c for c in changes if c.change_type == ChangeType.PERMISSIONS)
        self.assertEqual(perm_change.old_value, "0o0")

    def test_detect_removed(self):
        """Test changes detected for removed files."""
        entry = make_entry("/old", content_hash="h1", is_symlink=True)
        entry.symlink_target = "/target"

        changes = self.detector.detect_removed(entry, self.opts)

        types = {c.change_type for c in changes}
        self.assertIn(ChangeType.SYMLINK_TARGET, types)

        sym_change = next(c for c in changes if c.change_type == ChangeType.SYMLINK_TARGET)
        self.assertEqual(sym_change.old_value, "/target")
        self.assertEqual(sym_change.new_value, "")

    def test_detect_removed_with_xattrs(self):
        """Test detecting removal of a file with extended attributes."""
        entry = make_entry("/old")
        entry.xattrs = {"user.comment": b"important"}
        changes = self.detector.detect_removed(entry, self.opts)
        self.assertTrue(any(c.change_type == ChangeType.XATTRS for c in changes))

    def test_detect_added_content_only(self):
        """Test detect_added with content_only option."""
        self.opts.content_only = True
        entry = make_entry("/new", content_hash="h1", mode=0o755)

        changes = self.detector.detect_added(entry, self.opts)

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].change_type, ChangeType.CONTENT)

    def test_file_change_serialization(self):
        """Test FileChange.to_dict."""
        change = FileChange(ChangeType.CONTENT, "old", "new", "desc")
        data = change.to_dict()
        self.assertEqual(data["change_type"], "content")
        self.assertEqual(data["old_value"], "old")
