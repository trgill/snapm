# Copyright Red Hat
#
# tests/fsdiff/test_filetypes.py - Magic based file type detection tests.
#
# This file is part of the snapm project.
#
# SPDX-License-Identifier: Apache-2.0
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import magic
import os

from snapm.fsdiff.filetypes import FileTypeDetector, FileTypeCategory, FileTypeInfo

class TestFileTypeDetector(unittest.TestCase):
    def setUp(self):
        self.detector = FileTypeDetector()

    def test_FileTypeInfo(self):
        fti = FileTypeInfo("text/plain", "ASCII text", FileTypeCategory.TEXT, "utf-8")
        self.assertIn("MIME type: text/plain", str(fti))
        self.assertIn("Category: text", str(fti))

    @patch("snapm.fsdiff.filetypes.magic.detect_from_filename")
    def test_categorize_log_file(self, mock_magic):
        # magic might say plain text, but filename says .log
        mock_res = MagicMock()
        mock_res.mime_type = "text/plain"
        mock_res.name = "ASCII text"
        mock_res.encoding = "us-ascii"
        mock_magic.return_value = mock_res

        path = Path("/var/log/syslog")
        info = self.detector.detect_file_type(path, use_magic=True)

        self.assertEqual(info.category, FileTypeCategory.LOG)

    @patch("snapm.fsdiff.filetypes.magic.detect_from_filename")
    def test_categorize_json_config(self, mock_magic):
        mock_res = MagicMock()
        mock_res.mime_type = "application/json"
        mock_res.name = "JSON data"
        mock_res.encoding = "us-ascii"
        mock_magic.return_value = mock_res

        path = Path("/etc/app/config.json")
        info = self.detector.detect_file_type(path, use_magic=True)

        self.assertEqual(info.category, FileTypeCategory.CONFIG)

    def test_categorize_path_based_overrides(self):
        # Test logic in _categorize_file without mocking magic entirely
        # (unit testing the helper method directly if possible, or via public API)

        # .conf file -> CONFIG
        cat = self.detector._categorize_file("text/plain", Path("foo.conf"))
        self.assertEqual(cat, FileTypeCategory.CONFIG)

        # /etc/ file -> CONFIG
        cat = self.detector._categorize_file("text/plain", Path("/etc/passwd"))
        self.assertEqual(cat, FileTypeCategory.CONFIG)

        # .db file -> DATABASE
        cat = self.detector._categorize_file("application/octet-stream", Path("test.db"))
        self.assertEqual(cat, FileTypeCategory.DATABASE)

    # c9s magic does not have magic.error
    @unittest.skipIf(not hasattr(magic, "error"), "magic does not have magic.error")
    @patch("snapm.fsdiff.filetypes.magic.detect_from_filename")
    def test_detect_file_type_error(self, mock_magic):
        # Simulate magic library error
        mock_magic.side_effect = magic.error("magic failed")

        path = Path("/broken")
        info = self.detector.detect_file_type(path, use_magic=True)

        self.assertEqual(info.category, FileTypeCategory.UNKNOWN)
        self.assertEqual(info.mime_type, "application/octet-stream")

    def test_categorize_fallback(self):
        # Force a mimetype that doesn't match any rules
        cat = self.detector._categorize_file("application/x-strange-thing", Path("file.xyz"))
        self.assertEqual(cat, FileTypeCategory.BINARY)

    def test_detect_file_type_no_magic(self):
        """Test detection when magic is disabled or unavailable."""
        # 1. .sh extension detection
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as tmp:
            tmp.write("#!/bin/bash\necho hi")
            tmp.close()
            try:
                # Force no magic
                info = self.detector.detect_file_type(Path(tmp.name), use_magic=False)
                self.assertEqual(info.category, FileTypeCategory.SOURCE_CODE)
                self.assertEqual(info.mime_type, "application/x-sh")
            finally:
                os.unlink(tmp.name)

        # 2. Extension fallback
        info = self.detector.detect_file_type(Path("test.json"), use_magic=False)
        self.assertEqual(info.category, FileTypeCategory.CONFIG)
        self.assertEqual(info.mime_type, "application/json")

        # 3. Unknown fallback
        info = self.detector.detect_file_type(Path("unknown.blob"), use_magic=False)
        self.assertEqual(info.category, FileTypeCategory.BINARY)

    def test_categorize_extended_rules(self):
        """Test new categorization rules."""
        # Example: Log file in hidden dir? Or specific extension?
        # Assuming you added rules for things like .py, .service, etc.

        # Python script -> Text/Script
        cat = self.detector._categorize_file("text/x-python", Path("foo.py"))
        self.assertEqual(cat, FileTypeCategory.SOURCE_CODE)

        # Systemd unit -> Config (usually)
        cat = self.detector._categorize_file("text/plain", Path("bar.service"))
        self.assertEqual(cat, FileTypeCategory.CONFIG)

        # Systemd units -> CONFIG
        cat = self.detector._categorize_file("text/plain", Path("baz.slice"))
        self.assertEqual(cat, FileTypeCategory.CONFIG)

        # Python script -> SOURCE_CODE
        cat = self.detector._categorize_file("application/x-sh", Path("quux.sh"))
        self.assertEqual(cat, FileTypeCategory.SOURCE_CODE)

    @patch("snapm.fsdiff.filetypes.magic")
    def test_detect_file_type_magic_error(self, mock_magic):
        """Test behavior when libmagic raises an error."""
        # Setup magic to raise error
        mock_magic.error = Exception # Define error class
        mock_magic.detect_from_filename.side_effect = Exception("Magic failed")

        # Should return unknown binary
        info = self.detector.detect_file_type(Path("/file"), use_magic=True)
        self.assertEqual(info.category, FileTypeCategory.UNKNOWN)
        self.assertEqual(info.mime_type, "application/octet-stream")

