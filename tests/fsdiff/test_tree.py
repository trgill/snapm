# Copyright Red Hat
#
# tests/fsdiff/test_tree.py - Difference engine DiffTree tests
#
# This file is part of the snapm project.
#
# SPDX-License-Identifier: Apache-2.0
import unittest
from unittest.mock import MagicMock, patch
from typing import TextIO
import os

from snapm.fsdiff.tree import DiffTree, TreeNode
from snapm.fsdiff.engine import FsDiffResults, FsDiffRecord
from snapm.fsdiff.difftypes import DiffType
from snapm.fsdiff.options import DiffOptions
from snapm.fsdiff.changes import FileChange, ChangeType
from snapm.progress import TermControl

class TestTreeNode(unittest.TestCase):
    def test_init_valid(self):
        node = TreeNode("test")
        self.assertEqual(node.name, "test")
        self.assertIsNone(node.record)

    def test_init_with_record(self):
        rec = FsDiffRecord("/path", DiffType.ADDED)
        node = TreeNode("test", record=rec)
        self.assertEqual(node.record, rec)

    def test_init_moved_valid(self):
        rec = FsDiffRecord("/path", DiffType.MOVED)
        node = TreeNode("test", record=rec, to_or_from="to")
        self.assertEqual(node.to_or_from, "to")

    def test_init_moved_invalid_arg(self):
        rec = FsDiffRecord("/path", DiffType.MOVED)
        with self.assertRaises(ValueError):
            TreeNode("test", record=rec, to_or_from="invalid")

    def test_init_non_moved_invalid_arg(self):
        rec = FsDiffRecord("/path", DiffType.ADDED)
        with self.assertRaises(ValueError):
            TreeNode("test", record=rec, to_or_from="to")

class TestDiffTree(unittest.TestCase):
    def setUp(self):
        self.term_control = TermControl(color="never")
        self.root = TreeNode(os.sep)
        self.tree = DiffTree(self.root, 0, term_control=self.term_control)

    def test_init_root_none(self):
        with self.assertRaises(ValueError):
            DiffTree(None, 0)

    def test_unicode_chars(self):
        # Mock stdout encoding to utf-8
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.encoding = "utf-8"
            tc = TermControl(term_stream=mock_stdout)
            tree = DiffTree(self.root, 0, term_control=tc)
            self.assertEqual(tree.branch, "├── ")

    def test_ascii_chars_fallback(self):
        # Mock stdout encoding to ascii (cannot encode box chars)
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.encoding = "ascii"
            tc = TermControl(term_stream=mock_stdout)
            tree = DiffTree(self.root, 0, term_control=tc)
            self.assertEqual(tree.branch, "|-- ")

    def test_get_change_marker(self):
        # Added
        rec = FsDiffRecord("/a", DiffType.ADDED)
        node = TreeNode("a", rec)
        marker = self.tree.get_change_marker(rec, node)
        self.assertIn("[+]", marker)

        # Removed
        rec = FsDiffRecord("/a", DiffType.REMOVED)
        node = TreeNode("a", rec)
        marker = self.tree.get_change_marker(rec, node)
        self.assertIn("[-]", marker)

        # Moved From
        rec = FsDiffRecord("/a", DiffType.MOVED)
        node = TreeNode("a", rec, to_or_from="from")
        marker = self.tree.get_change_marker(rec, node)
        self.assertIn("[<]", marker)

        # Moved To
        rec = FsDiffRecord("/b", DiffType.MOVED)
        node = TreeNode("b", rec, to_or_from="to")
        marker = self.tree.get_change_marker(rec, node)
        self.assertIn("[>]", marker)

        # None record
        self.assertEqual(self.tree.get_change_marker(None, node), "")

    def test_get_change_marker_invalid_move(self):
        rec = FsDiffRecord("/a", DiffType.MOVED)
        # Manually bypass TreeNode validation or create inconsistent state
        node = TreeNode("a", rec, to_or_from="to")
        node.to_or_from = "bad"
        with self.assertRaises(ValueError):
            self.tree.get_change_marker(rec, node)

    def test_build_tree_empty(self):
        results = FsDiffResults([], DiffOptions())
        tree = DiffTree.build_tree(results)
        self.assertEqual(tree.node_count, 0)
        self.assertEqual(tree.render(), "/")

    def test_build_and_render_simple(self):
        # /dir (MODIFIED)
        # /dir/file (ADDED)
        rec1 = FsDiffRecord("/dir", DiffType.MODIFIED)
        rec2 = FsDiffRecord("/dir/file", DiffType.ADDED)
        rec3 = FsDiffRecord("/dir2", DiffType.MODIFIED)
        results = FsDiffResults([rec1, rec2, rec3], DiffOptions())

        term_control = MagicMock(spec=TermControl)
        term_control.term_stream = MagicMock(spec=TextIO)
        term_control.term_stream.encoding = "ascii"
        term_control.columns = 80

        term_control.BLACK: str = ""  #: Black foreground color
        term_control.BLUE: str = ""  #: Blue foreground color
        term_control.GREEN: str = ""  #: Green foreground color
        term_control.CYAN: str = ""  #: Cyan foreground color
        term_control.RED: str = ""  #: Red foreground color
        term_control.MAGENTA: str = ""  #: Magenta foreground color
        term_control.YELLOW: str = ""  #: Yellow foreground color
        term_control.WHITE: str = ""  #: White foreground color
        term_control.NORMAL: str = ""  #: Reset all properties

        tree = DiffTree.build_tree(results, term_control=term_control)
        output = tree.render()
        print(output)
        self.assertIn("|-- [*] dir", output)
        self.assertIn("`-- [+] file", output)

    def test_build_tree_root_record(self):
        # Record for "/"
        rec = FsDiffRecord("/", DiffType.MODIFIED)
        results = FsDiffResults([rec], DiffOptions())
        tree = DiffTree.build_tree(results, color="never")
        output = tree.render()
        self.assertIn("[*] /", output)

    def test_build_tree_orphan_move(self):
        # Move /a to /x/y where /x is not in records (orphan adoption logic)
        rec1 = FsDiffRecord("/", DiffType.MODIFIED)
        rec2 = FsDiffRecord("/x", DiffType.MODIFIED)
        rec3 = FsDiffRecord("/a", DiffType.MOVED)
        rec3.moved_from = "/a"
        rec3.moved_to = "/x/y"

        term_control = MagicMock(spec=TermControl)
        term_control.term_stream = MagicMock(spec=TextIO)
        term_control.term_stream.encoding = "ascii"
        term_control.columns = 80

        term_control.BLACK: str = ""  #: Black foreground color
        term_control.BLUE: str = ""  #: Blue foreground color
        term_control.GREEN: str = ""  #: Green foreground color
        term_control.CYAN: str = ""  #: Cyan foreground color
        term_control.RED: str = ""  #: Red foreground color
        term_control.MAGENTA: str = ""  #: Magenta foreground color
        term_control.YELLOW: str = ""  #: Yellow foreground color
        term_control.WHITE: str = ""  #: White foreground color
        term_control.NORMAL: str = ""  #: Reset all properties

        results = FsDiffResults([rec1, rec2, rec3], DiffOptions())
        tree = DiffTree.build_tree(results, term_control=term_control)
        output = tree.render()
        print(output)

        # Should see 'a' marked as source [<]
        self.assertIn("[<] a", output) # \x1b[0m is reset code from TermControl default
        # Should see 'x' created as parent
        self.assertIn("x", output)
        # Should see 'y' marked as dest [>]
        self.assertIn("[>] y", output)

    def test_build_tree_rename_same_dir(self):
        # Move /a to /b
        rec1 = FsDiffRecord("/", DiffType.MODIFIED)
        rec2 = FsDiffRecord("/a", DiffType.MOVED)
        rec2.moved_from = "/a"
        rec2.moved_to = "/b"

        results = FsDiffResults([rec1, rec2], DiffOptions())
        tree = DiffTree.build_tree(results, color="never")
        output = tree.render()

        self.assertIn("[<] a -> /b", output)
        self.assertIn("[>] b <- /a", output)

    def test_render_full_desc(self):
        rec = FsDiffRecord("/file", DiffType.MODIFIED)
        rec.add_change(FileChange(ChangeType.CONTENT, description="content changed"))
        results = FsDiffResults([rec], DiffOptions())

        tree = DiffTree.build_tree(results, color="never")
        output = tree.render(desc="full")
        self.assertIn("(content changed)", output)

    def test_render_short_desc(self):
        rec = FsDiffRecord("/file", DiffType.MODIFIED)
        rec.add_change(FileChange(ChangeType.CONTENT, description="content changed"))
        results = FsDiffResults([rec], DiffOptions())

        tree = DiffTree.build_tree(results, color="never")
        output = tree.render(desc="short")
        self.assertIn("(content)", output)

    def test_render_errors(self):

        badtree = DiffTree(self.root, 0, term_control=self.term_control)
        badtree.root = None
        # Undefined node
        with self.assertRaises(ValueError):
            badtree.render()

        # Cannot render subtree without context (private var check)
        self.tree._rendered = None
        child = TreeNode("child")
        with self.assertRaises(RuntimeError):
            self.tree.render(node=child)

        # Cannot restart render
        self.tree._rendered = []
        with self.assertRaises(RuntimeError):
            self.tree.render(node=self.root)

    def test_build_tree_moved_validation(self):
        rec = FsDiffRecord("/a", DiffType.MOVED)
        # Missing moved_from/to
        results = FsDiffResults([rec], DiffOptions())
        with self.assertRaises(ValueError):
            DiffTree.build_tree(results)

    def test_interrupt_build_tree(self):
        rec = FsDiffRecord("/a", DiffType.MODIFIED)
        results = FsDiffResults([rec], DiffOptions())
        with patch("snapm.fsdiff.tree.ProgressFactory.get_progress") as mock_prog:
            mock_prog.return_value.start.side_effect = KeyboardInterrupt
            with self.assertRaises(KeyboardInterrupt):
                DiffTree.build_tree(results)
