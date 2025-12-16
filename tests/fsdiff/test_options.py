# Copyright Red Hat
#
# tests/fsdiff/test_options.py - DiffOptions tests.
#
# This file is part of the snapm project.
#
# SPDX-License-Identifier: Apache-2.0
import unittest
from argparse import Namespace

from snapm.fsdiff.options import DiffOptions


class TestDiffOptions(unittest.TestCase):
    def test_DiffOptions__str__(self):
        opts = DiffOptions(ignore_timestamps=True, file_patterns=["*.txt"])
        s = str(opts)
        self.assertIn("ignore_timestamps=True", s)
        self.assertIn("file_patterns=*.txt", s)

    def test_from_cmd_args(self):
        """Test initialization from argparse Namespace."""
        args = Namespace(
            ignore_timestamps=True,
            max_file_size=1024,
            unknown_arg="ignored"
        )
        opts = DiffOptions.from_cmd_args(args)

        self.assertTrue(opts.ignore_timestamps)
        self.assertEqual(opts.max_file_size, 1024)
        # Should use defaults for missing args
        self.assertFalse(opts.ignore_ownership)
