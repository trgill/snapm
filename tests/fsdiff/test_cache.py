# Copyright Red Hat
#
# tests/fsdiff/test_cache.py - Diff cache tests
#
# This file is part of the snapm project.
#
# SPDX-License-Identifier: Apache-2.0
import unittest
import os
import stat
import lzma
import pickle
from unittest.mock import MagicMock, patch, mock_open
from uuid import uuid4

from snapm import SnapmSystemError, SnapmNotFoundError, SnapmInvalidIdentifierError
from snapm.fsdiff import cache
from snapm.fsdiff.options import DiffOptions
from snapm.fsdiff.engine import FsDiffResults

class TestCache(unittest.TestCase):
    def setUp(self):
        self.mount_a = MagicMock()
        self.mount_a.name = "root"
        self.mount_a.snapset = None  # Triggers _root_uuid

        self.mount_b = MagicMock()
        self.mount_b.name = "snap1"
        self.mount_b.snapset.uuid = uuid4()

        self.results = MagicMock(spec=FsDiffResults)
        self.results.timestamp = 1600000000
        self.results.options = DiffOptions()

    @patch("os.makedirs")
    @patch("os.path.exists")
    @patch("os.lstat")
    @patch("os.stat")
    @patch("os.chmod")
    def test_check_cache_dir_success(self, mock_chmod, mock_stat, mock_lstat, mock_exists, mock_makedirs):
        # Case 1: Directory does not exist, create it
        mock_exists.return_value = False
        mock_stat.return_value.st_mode = 0o700
        cache._check_cache_dir("/tmp/cache", 0o700, "test")
        mock_makedirs.assert_called_with("/tmp/cache", mode=0o700, exist_ok=True)

        # Case 2: Directory exists, permissions are correct
        mock_exists.return_value = True
        mock_lstat.return_value.st_mode = stat.S_IFDIR | 0o700
        mock_stat.return_value.st_mode = stat.S_IFDIR | 0o700
        cache._check_cache_dir("/tmp/cache", 0o700, "test")
        mock_chmod.assert_not_called()

        # Case 3: Directory exists, permissions wrong, fix them
        mock_stat.side_effect = [
            os.stat_result((stat.S_IFDIR | 0o755, 0, 0, 0, 0, 0, 0, 0, 0, 0)), # Initial check
            os.stat_result((stat.S_IFDIR | 0o700, 0, 0, 0, 0, 0, 0, 0, 0, 0))  # Post-fix verify
        ]
        cache._check_cache_dir("/tmp/cache", 0o700, "test")
        mock_chmod.assert_called_with("/tmp/cache", 0o700)

    @patch("os.path.exists", return_value=True)
    @patch("os.lstat")
    def test_check_cache_dir_symlink_error(self, mock_lstat, mock_exists):
        mock_lstat.return_value.st_mode = stat.S_IFLNK
        with self.assertRaisesRegex(SnapmSystemError, "is a symlink"):
            cache._check_cache_dir("/path", 0o700, "test")

    @patch("os.path.exists", return_value=True)
    @patch("os.lstat")
    def test_check_cache_dir_not_dir_error(self, mock_lstat, mock_exists):
        mock_lstat.return_value.st_mode = stat.S_IFREG
        with self.assertRaisesRegex(SnapmSystemError, "is not a directory"):
            cache._check_cache_dir("/path", 0o700, "test")

    @patch("os.makedirs", side_effect=OSError("mkdir failed"))
    @patch("os.path.exists", return_value=False)
    def test_check_cache_dir_create_fail(self, mock_exists, mock_makedirs):
        with self.assertRaisesRegex(SnapmSystemError, "Failed to create"):
            cache._check_cache_dir("/path", 0o700, "test")

    @patch("os.chmod", side_effect=OSError("chmod failed"))
    @patch("os.path.exists", return_value=True)
    @patch("os.lstat")
    @patch("os.stat")
    def test_check_cache_dir_chmod_fail(self, mock_stat, mock_lstat, mock_exists, mock_chmod):
        mock_lstat.return_value.st_mode = stat.S_IFDIR
        mock_stat.return_value.st_mode = stat.S_IFDIR | 0o755 # Wrong perms
        with patch("os.makedirs"):
            with self.assertRaisesRegex(SnapmSystemError, "Failed to set permissions"):
                cache._check_cache_dir("/path", 0o700, "test")

    @patch("os.chmod")
    @patch("os.path.exists", return_value=True)
    @patch("os.lstat")
    @patch("os.stat")
    def test_check_cache_dir_verify_fail(self, mock_stat, mock_lstat, mock_exists, mock_chmod):
        mock_lstat.return_value.st_mode = stat.S_IFDIR
        # Stat returns wrong permissions even after chmod (simulated)
        mock_stat.return_value.st_mode = stat.S_IFDIR | 0o755
        with patch("os.makedirs"):
            with self.assertRaisesRegex(SnapmSystemError, "incorrect permissions"):
                cache._check_cache_dir("/path", 0o700, "test")

    def test_cache_name_identity_error(self):
        # mount_a == mount_b
        with self.assertRaisesRegex(SnapmInvalidIdentifierError, "mount_a == mount_b"):
            cache._cache_name(self.mount_a, self.mount_a, self.results)

    @patch("snapm.fsdiff.cache._check_dirs")
    @patch("lzma.open")
    @patch("pickle.dump")
    def test_save_cache(self, mock_dump, mock_lzma, mock_check):
        cache.save_cache(self.mount_a, self.mount_b, self.results)
        mock_check.assert_called_once()
        mock_lzma.assert_called_once()
        mock_dump.assert_called_with(self.results, mock_lzma.return_value.__enter__.return_value)

    @patch("snapm.fsdiff.cache._check_dirs")
    @patch("os.listdir")
    @patch("lzma.open")
    @patch("pickle.load")
    def test_load_cache_success(self, mock_load, mock_lzma, mock_listdir, mock_check):
        # Setup matching filename
        uuid_a = cache._root_uuid(self.mount_a)
        uuid_b = self.mount_b.snapset.uuid
        # Ensure timestamp is fresh enough
        valid_ts = cache.floor(cache.datetime.now().timestamp())
        fname = f"{uuid_a}.{uuid_b}.123.{valid_ts}.cache"

        mock_listdir.return_value = [fname]

        # Setup returned object with matching options
        cached_res = MagicMock()
        cached_res.options = self.results.options
        mock_load.return_value = cached_res

        res = cache.load_cache(self.mount_a, self.mount_b, self.results.options)
        self.assertEqual(res, cached_res)

    @patch("snapm.fsdiff.cache._check_dirs")
    def test_load_cache_identity_error(self, mock_check):
        with self.assertRaisesRegex(SnapmInvalidIdentifierError, "mount_a == mount_b"):
            cache.load_cache(self.mount_a, self.mount_a, DiffOptions())

    @patch("snapm.fsdiff.cache._check_dirs")
    @patch("os.listdir", return_value=["random_file.txt", "bad.uuid.1.2.cache", "a.b.c.not_int.cache"])
    def test_load_cache_ignores_malformed(self, mock_listdir, mock_check):
        # Should iterate over garbage without crashing and raise NotFound
        with self.assertRaises(SnapmNotFoundError):
            cache.load_cache(self.mount_a, self.mount_b, DiffOptions())

    @patch("snapm.fsdiff.cache._check_dirs")
    @patch("os.listdir")
    @patch("os.unlink")
    def test_load_cache_prunes_expired(self, mock_unlink, mock_listdir, mock_check):
        # Setup expired filename
        uuid_a = cache._root_uuid(self.mount_a)
        uuid_b = self.mount_b.snapset.uuid
        old_ts = 1000 # Very old
        fname = f"{uuid_a}.{uuid_b}.123.{old_ts}.cache"

        mock_listdir.return_value = [fname]

        with self.assertRaises(SnapmNotFoundError):
            cache.load_cache(self.mount_a, self.mount_b, DiffOptions(), expires=60)

        mock_unlink.assert_called()

    @patch("snapm.fsdiff.cache._check_dirs")
    @patch("os.listdir")
    @patch("lzma.open")
    @patch("pickle.load")
    def test_load_cache_options_mismatch(self, mock_load, mock_lzma, mock_listdir, mock_check):
        uuid_a = cache._root_uuid(self.mount_a)
        uuid_b = self.mount_b.snapset.uuid
        valid_ts = cache.floor(cache.datetime.now().timestamp())
        fname = f"{uuid_a}.{uuid_b}.123.{valid_ts}.cache"

        mock_listdir.return_value = [fname]

        # Returned object has DIFFERENT options
        cached_res = MagicMock()
        cached_res.options = DiffOptions(content_only=True) # different
        mock_load.return_value = cached_res

        with self.assertRaises(SnapmNotFoundError):
            cache.load_cache(self.mount_a, self.mount_b, DiffOptions(content_only=False))
