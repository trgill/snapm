# Copyright Red Hat
#
# tests/fsdiff/test_treewalk.py - FsEntry tests.
#
# This file is part of the snapm project.
#
# SPDX-License-Identifier: Apache-2.0
import unittest
import tempfile
import stat
import os
from unittest.mock import MagicMock, patch
from pathlib import Path

from snapm.fsdiff.filetypes import FileTypeInfo, FileTypeCategory
from snapm.fsdiff.fsdiffer import FsDiffer
from snapm.fsdiff.options import DiffOptions
from snapm.fsdiff.treewalk import FsEntry, TreeWalker, _stat_to_dict
# Mock Mount for typing/usage
from snapm.manager._mounts import Mount

from ._util import make_entry


class TestTreeWalker(unittest.TestCase):
    def test_TreeWalker(self):
        """Test TreeWalker.__init__()"""
        walker = TreeWalker(DiffOptions())
        self.assertEqual(walker.hash_algorithm, "sha256")
        self.assertIn("/proc/*", walker.exclude_patterns)

    def test_TreeWalker_excludes_logic(self):
        """Test exclude pattern logic in constructor."""
        # Case 1: Default system dirs included
        opts = DiffOptions(include_system_dirs=True)
        walker = TreeWalker(opts)
        self.assertEqual(walker.exclude_patterns, [])

        # Case 2: Custom excludes + system dirs default (implicit)
        opts = DiffOptions(exclude_patterns=["/custom/*"])
        walker = TreeWalker(opts)
        self.assertIn("/custom/*", walker.exclude_patterns)
        self.assertIn("/proc/*", walker.exclude_patterns)

        # Case 3: Only system dirs (default)
        opts = DiffOptions()
        walker = TreeWalker(opts)
        self.assertIn("/proc/*", walker.exclude_patterns)

    def test_stat_to_dict(self):
        # Mock a stat result
        st = os.stat_result((0o644, 1, 2, 1, 1000, 1000, 100, 0, 0, 0))
        d = _stat_to_dict(st)
        self.assertEqual(d["st_mode"], 0o644)
        self.assertEqual(d["st_size"], 100)

    def test_TreeWalker_race_vanished(self):
        walker = TreeWalker(DiffOptions())
        mount = MagicMock(spec=Mount)
        mount.root = "/tmp"  # noqa: S108
        mount.name = "tmp"
        with patch("os.walk", return_value=[("/tmp", [], ["vanished"])]), \
             patch("os.path.exists", return_value=False), \
             patch("os.lstat", side_effect=FileNotFoundError):
            tree = walker.walk_tree(mount)
            self.assertNotIn("/tmp/vanished", tree)
            self.assertNotIn("vanished", tree)

    def test_get_xattrs_oserror(self):
        """Cover OSError handling in _get_xattrs."""
        # This requires patching os.listxattr to raise OSError
        # We can't easily access the inner function, but we can trigger it via FsEntry init
        with patch("os.path.exists", return_value=True), \
             patch("os.stat"), \
             patch("os.listxattr", side_effect=OSError("Mock error")):

            entry = FsEntry("/file", "", os.stat_result((0o644,)*10))
            self.assertEqual(entry.xattrs, {})

    def test_walk_tree_throbber_callback(self):
        """Verify the throbber callback mechanism."""
        mount = MagicMock(spec=Mount)
        mount.root = "/root"
        mount.name = "TestRoot"

        # We want to verify the internal _throb function is called.
        # It's passed to os.walk list comprehension.
        # We can detect this if we mock ProgressFactory to return a mock throbber
        # and verify the throbber's .throb() method is called.

        walker = TreeWalker(DiffOptions())
        with patch("snapm.fsdiff.treewalk.ProgressFactory.get_throbber") as mock_get_throb:
            mock_throbber = MagicMock()
            mock_get_throb.return_value = mock_throbber

            # Make os.walk return at least one item to trigger the loop
            with patch("os.walk", return_value=[("/root", [], ["file"])]), \
                 patch("os.lstat") as mock_lstat:
                mock_lstat.return_value.st_mode = 0o0
                walker.walk_tree(mount)

            # Verify start/end called
            mock_throbber.start.assert_called()
            mock_throbber.end.assert_called()
            # Verify throb called (for the root item + walk items)
            self.assertTrue(mock_throbber.throb.called)


class TestFsEntry(unittest.TestCase):
    def test_FsEntry__str__(self):
        """Cover FsEntry.__str__ and xattrs"""
        entry = make_entry("/foo")
        entry.xattrs = {"user.comment": "test"}
        entry.symlink_target = "/target"
        s = str(entry)
        self.assertIn("extended_attributes", s)
        self.assertIn("user.comment=test", s)
        self.assertIn("symlink_target", s)

    def test_special_file_block(self):
        """Test FsEntry properties for special file types (block)."""
        # Block Device
        entry = make_entry("/dev/sda", mode=stat.S_IFBLK | 0o660)
        self.assertTrue(entry.is_block)
        self.assertEqual(entry.type_desc, "block device")

    def test_special_file_char(self):
        """Test FsEntry properties for special file types (char)."""
        # Char Device
        entry = make_entry("/dev/null", mode=stat.S_IFCHR | 0o666)
        self.assertTrue(entry.is_char)
        self.assertEqual(entry.type_desc, "char device")

    def test_special_file_pipe(self):
        """Test FsEntry properties for special file types (pipe)."""
        # FIFO (Named Pipe)
        entry = make_entry("/tmp/pipe", mode=stat.S_IFIFO | 0o600)  # noqa: S108
        self.assertTrue(entry.is_fifo)
        self.assertEqual(entry.type_desc, "FIFO")

    def test_special_file_sock(self):
        """Test FsEntry properties for special file types (sock)."""
        # Socket
        entry = make_entry("/tmp/sock", mode=stat.S_IFSOCK | 0o600)  # noqa: S108
        self.assertTrue(entry.is_sock)
        self.assertEqual(entry.type_desc, "socket")

    def test_special_file_unknown(self):
        """Test FsEntry properties for special file types (unknown)."""
        # Fallback "other" (unlikely in standard POSIX, but good for logic coverage)
        # Creating an entry with 0 mode (no type bits)
        entry = make_entry("/unknown", mode=0)
        # Reset mode to 0 explicitly as make_entry might default it
        entry.mode = 0
        self.assertEqual(entry.type_desc, "other")

    def test_is_text_like(self):
        """Test is_text_like logic."""
        # 1. Not a file -> False
        entry = make_entry("/dir", is_dir=True)
        self.assertFalse(entry.is_text_like)

        # 2. File without type info -> False (default assumption)
        entry = make_entry("/file")
        entry.file_type_info = None
        self.assertFalse(entry.is_text_like)

        # 3. File with text type info -> True
        entry = make_entry("/file.txt")
        entry.file_type_info = FileTypeInfo("text/plain", "Text", FileTypeCategory.TEXT)
        self.assertTrue(entry.is_text_like)

    def test_fs_entry_type_desc_standard(self):
        """Cover type_desc branches for standard types in treewalk.py."""
        # snapm.fsdiff.treewalk: standard type_desc branches
        # File
        entry_file = make_entry("/file", mode=stat.S_IFREG)
        self.assertEqual(entry_file.type_desc, "file")

        # Directory
        entry_dir = make_entry("/dir", is_dir=True)
        self.assertEqual(entry_dir.type_desc, "directory")

        # Symlink
        entry_link = make_entry("/link", is_symlink=True)
        self.assertEqual(entry_link.type_desc, "symbolic link")

    def test_FsEntry_to_dict(self):
        """Test serialization of FsEntry, including xattr decoding."""
        entry = make_entry("/file", content_hash="hash")
        # Add xattrs: one utf-8, one binary
        entry.xattrs = {
            "user.utf8": b"value",
            "user.bin": b"\xFF\xFF"
        }

        data = entry.to_dict()

        self.assertEqual(data["path"], "/file")
        self.assertEqual(data["content_hash"], "hash")
        # Verify UTF-8 decoding
        self.assertEqual(data["xattrs"]["user.utf8"], "value")
        # Verify hex fallback
        self.assertEqual(data["xattrs"]["user.bin"], "ffff")


class TestTreeWalkFull(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)

        # Create a file structure:
        # /root/
        #   file_a (content="hash_a")
        #   dir_b/
        #     file_c (content="hash_c")
        #   link_d -> file_a (relative symlink)
        #   abs_link -> /root/file_a (absolute symlink)
        #   broken_e -> nonexistent (broken symlink)
        #   exclude_me/
        #     file_f

        (self.root / "file_a").write_text("hash_a")
        (self.root / "dir_b").mkdir()
        (self.root / "dir_b" / "file_c").write_text("hash_c")
        (self.root / "link_d").symlink_to("file_a")
        (self.root / "abs_link").symlink_to((self.root / "file_a").resolve())
        (self.root / "broken_e").symlink_to("nonexistent")
        (self.root / "exclude_me").mkdir()
        (self.root / "exclude_me" / "file_f").write_text("ignored")

        self.opts = DiffOptions()
        # Ensure we capture content hash by default
        self.opts.include_content_hash = True

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_treewalk_basic(self):
        """Test a standard tree walk with hashing and basic properties."""
        walker = TreeWalker(self.opts)
        mount = MagicMock(spec=Mount)
        mount.root = str(self.root)
        mount.name = "test_mount"

        # Walk
        tree = walker.walk_tree(mount, strip_prefix=str(self.root))

        # Verify entries exist (paths are relative due to strip_prefix)
        self.assertIn("/file_a", tree)
        self.assertIn("/dir_b", tree)
        self.assertIn("/dir_b/file_c", tree)
        self.assertIn("/link_d", tree)
        self.assertIn("/abs_link", tree)
        self.assertIn("/broken_e", tree)
        self.assertIn("/exclude_me", tree)

        # Verify FsEntry properties
        self.assertTrue(tree["/file_a"].is_file)
        self.assertIsNotNone(tree["/file_a"].content_hash)
        # MD5 of "hash_a" is 74b8... but default is sha256
        # Just check it is present and looks like a hash
        self.assertEqual(len(tree["/file_a"].content_hash), 64) # sha256 length

        self.assertTrue(tree["/dir_b"].is_dir)

        # Symlink checks
        self.assertTrue(tree["/link_d"].is_symlink)
        self.assertEqual(tree["/link_d"].symlink_target, "file_a")
        self.assertFalse(tree["/link_d"].broken_symlink)

        # Absolute symlink check
        self.assertTrue(tree["/abs_link"].is_symlink)
        self.assertTrue(os.path.isabs(tree["/abs_link"].symlink_target))
        self.assertFalse(tree["/abs_link"].broken_symlink)

        # Broken symlink checks
        self.assertTrue(tree["/broken_e"].is_symlink)
        self.assertTrue(tree["/broken_e"].broken_symlink)
        self.assertIsNone(tree["/broken_e"].content_hash)

    def test_treewalk_exclusions(self):
        """Test exclude_patterns functionality."""
        self.opts.exclude_patterns = ["/exclude_me*"]
        walker = TreeWalker(self.opts)
        mount = MagicMock(spec=Mount)
        mount.root = str(self.root)
        mount.name = "test_mount"

        tree = walker.walk_tree(mount, strip_prefix=str(self.root))

        self.assertNotIn("/exclude_me", tree)
        self.assertNotIn("/exclude_me/file_f", tree)
        self.assertIn("/file_a", tree)

    def test_treewalk_file_patterns(self):
        """Test file_patterns (inclusion filter)."""
        self.opts.file_patterns = ["/file_a"]
        walker = TreeWalker(self.opts)
        mount = MagicMock(spec=Mount)
        mount.root = str(self.root)
        mount.name = "test_mount"

        tree = walker.walk_tree(mount, strip_prefix=str(self.root))

        self.assertIn("/file_a", tree)
        self.assertNotIn("/dir_b/file_c", tree)

    def test_treewalk_follow_symlinks(self):
        """Test behavior when follow_symlinks is True."""
        self.opts.follow_symlinks = True
        walker = TreeWalker(self.opts)
        mount = MagicMock(spec=Mount)
        mount.root = str(self.root)
        mount.name = "test_mount"

        tree = walker.walk_tree(mount, strip_prefix=str(self.root))

        # link_d points to file_a.
        # When followed, it is treated as the target (file).
        self.assertIn("/link_d", tree)
        self.assertTrue(tree["/link_d"].is_file)
        self.assertFalse(tree["/link_d"].is_symlink)

        # broken_e is dangling.
        # Code path should fallback to treating it as a symlink entry (lstat)
        self.assertIn("/broken_e", tree)
        self.assertTrue(tree["/broken_e"].is_symlink)

    def test_treewalk_hash_algo(self):
        """Test using a non-default hash algorithm (md5)."""
        walker = TreeWalker(self.opts, hash_algorithm="md5")
        mount = MagicMock(spec=Mount)
        mount.root = str(self.root)
        mount.name = "test_mount"

        tree = walker.walk_tree(mount, strip_prefix=str(self.root))
        # echo -n "hash_a" | md5sum -> f2920f6fa5af12a433eaac7433c7086b
        self.assertEqual(tree["/file_a"].content_hash, "f2920f6fa5af12a433eaac7433c7086b")

    def test_treewalk_invalid_hash_algo(self):
        """Test error when initializing with invalid hash algorithm."""
        with self.assertRaises(ValueError):
            TreeWalker(self.opts, hash_algorithm="fake_algo")

    def test_fsentry_xattrs(self):
        """Test xattr retrieval in FsEntry (mocked)."""
        # Patch os.listxattr and os.getxattr
        with patch("os.listxattr", return_value=["user.myattr"]), \
             patch("os.getxattr", return_value=b"myvalue"):
            path = str(self.root / "file_a")
            stat_res = os.stat(path)

            entry = FsEntry(path, str(self.root), stat_res)
            self.assertEqual(entry.xattrs, {"user.myattr": b"myvalue"})

    def test_fsentry_xattrs_missing_file(self):
        """Test xattr retrieval when file is missing (race condition logic)."""
        path = str(self.root / "file_a")
        stat_res = os.stat(path)

        # Patch os.path.exists to return False inside FsEntry initialization
        # This covers the 'if not os.path.exists(path): return {}' branch in _get_xattrs
        with patch("os.path.exists", return_value=False):
            entry = FsEntry(path, str(self.root), stat_res)
            self.assertEqual(entry.xattrs, {})

    def test_fsdiffer_compare_roots(self):
        """Test high-level FsDiffer.compare_roots."""
        differ = FsDiffer(MagicMock(), self.opts)

        mount_a = MagicMock()
        mount_a.root = str(self.root)
        mount_a.name = "mntA"

        # For B, use identical root -> No diffs
        mount_b = MagicMock()
        mount_b.root = str(self.root)
        mount_b.name = "mntB"

        diffs = differ.compare_roots(mount_a, mount_b)
        self.assertEqual(len(diffs), 0)

        # Now Create B as a different dir
        with tempfile.TemporaryDirectory() as tmp_b:
            # Add modified file
            (Path(tmp_b) / "file_a").write_text("changed_content")
            mount_b.root = tmp_b

            # A has file_a, dir_b, etc.
            # B has only file_a (modified).
            # Expect: file_a MODIFIED, others REMOVED.
            diffs2 = differ.compare_roots(mount_a, mount_b)
            self.assertTrue(len(diffs2) > 0)

            file_a_diff = next(d for d in diffs2 if d.path.endswith("/file_a"))
            self.assertEqual(file_a_diff.diff_type.value, "modified")

    def test_treewalk_interrupt(self):
        """Test KeyboardInterrupt handling during walk."""
        walker = TreeWalker(self.opts)
        mount = MagicMock(spec=Mount)
        mount.root = str(self.root)
        mount.name = "test_mount"

        with patch("os.walk", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                walker.walk_tree(mount)

    def test_max_content_hash_size(self):
        """Test skipping hash calculation for large files."""
        # file_a is 6 bytes. Set limit to 1 byte.
        self.opts.max_content_hash_size = 1
        walker = TreeWalker(self.opts)
        mount = MagicMock(spec=Mount)
        mount.root = str(self.root)
        mount.name = "test_mount"

        tree = walker.walk_tree(mount, strip_prefix=str(self.root))
        self.assertIsNone(tree["/file_a"].content_hash)
