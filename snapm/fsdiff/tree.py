# Copyright Red Hat
#
# snapm/fsdiff/tree.py - Snapshot Manager fs diff tree renderer
#
# This file is part of the snapm project.
#
# SPDX-License-Identifier: Apache-2.0
"""
File system diff tree rendering
"""
from typing import Dict, List, Optional, TYPE_CHECKING
from collections import defaultdict
import logging
import os

from snapm import SNAPM_SUBSYSTEM_FSDIFF

from ..progress import ProgressFactory, TermControl
from .difftypes import DiffType

if TYPE_CHECKING:
    from .engine import FsDiffRecord, FsDiffResults

_log = logging.getLogger(__name__)

_log_debug = _log.debug
_log_info = _log.info
_log_warn = _log.warning
_log_error = _log.error


def _log_debug_fsdiff(msg, *args, **kwargs):
    """A wrapper for fsdiff subsystem debug logs."""
    _log.debug(msg, *args, extra={"subsystem": SNAPM_SUBSYSTEM_FSDIFF}, **kwargs)


class TreeNode:
    """Internal class representing difference tree nodes."""

    def __init__(
        self,
        name: str,
        record: Optional["FsDiffRecord"] = None,
        to_or_from: Optional[str] = None,
    ):
        """
        Initialise a new ``TreeNode`` with the specified name and diff record.

        :param name: The name of this node.
        :type name: ``str``
        :param record: The diff record for this node.
        :type record: ``Optional["FsDiffRecord"]``
        :param to_or_from: "to" if this is a destination move node, "from" if this
                           is a source move node, or None otherwise.
        :type to_or_from: ``Optional[str]``
        """
        self.name: str = name
        self.record: "Optional[FsDiffRecord]" = record  # None for intermediate dirs
        self.children: Dict[str, TreeNode] = {}

        if record is not None:
            if record.diff_type != DiffType.MOVED and to_or_from is not None:
                raise ValueError(
                    f"Invalid argument for non-MOVED record: to_or_from={to_or_from}"
                )
            if record.diff_type == DiffType.MOVED and to_or_from not in (
                "to",
                "from",
            ):
                raise ValueError(
                    f"Invalid to_or_from argument for MOVED record: {to_or_from}"
                )

        self.to_or_from = to_or_from


class DiffTree:
    """Top level interface for rendering difference trees"""

    def __init__(
        self,
        root: TreeNode,
        node_count: int,
        color: str = "auto",
        term_control: Optional[TermControl] = None,
    ):
        """
        Initialise a new ``DiffTree` object.

        :param root: The root node for this ``DiffTree`.
        :type root: ``TreeNode``
        :param color: A string to control color tree rendering: "auto",
                      "always", or "never".
        :type color: ``str``
        :param term_control: An optional ``TermControl`` instance to use for
                             formatting. The supplied instance overrides any
                             ``color`` argument if set.
        :type term_control: ``Optional[TermControl]``
        """
        if root is None:
            raise ValueError("Root node is undefined")

        self.root: TreeNode = root
        self.node_count = node_count

        # Set up color modes
        self.term_control: TermControl = term_control or TermControl(color=color)

        self._rendered: Optional[List[str]] = None

        # Default to ASCII tree drawing characters
        self.branch = "|-- "
        self.last = "`-- "
        self.vbar = "|"

        self.marker_map = {
            DiffType.ADDED: (self.term_control.GREEN, "[+]"),
            DiffType.REMOVED: (self.term_control.RED, "[-]"),
            DiffType.MODIFIED: (self.term_control.YELLOW, "[*]"),
            DiffType.MOVED: (self.term_control.CYAN, "[x]"),
            DiffType.TYPE_CHANGED: (self.term_control.BLUE, "[!]"),
        }

        encoding = getattr(self.term_control.term_stream, "encoding", None)

        if not encoding:
            return
        try:
            "└─├│".encode(encoding)
            self.branch = "├── "
            self.last = "└── "
            self.vbar = "│"
        except UnicodeEncodeError:
            return

    def get_change_marker(
        self, record: Optional["FsDiffRecord"], node: TreeNode
    ) -> str:
        """
        Return color-coded change mark for difference record.

        :param record: The file system diff record to generate a marker for.
        :type record: ``Optional["FsDiffRecord"]``
        :returns: Change marker with embedded color codes.
        :rtype: ``str``
        """
        if not record:
            return ""

        if record.diff_type == DiffType.MOVED:
            color, _ = self.marker_map.get(record.diff_type, ("", ""))
            if node.to_or_from == "from":
                marker = "[<]"
            elif node.to_or_from == "to":
                marker = "[>]"
            else:
                raise ValueError(
                    "Illegal move direction for DiffType.MOVED: " + str(node.to_or_from)
                )
        else:
            color, marker = self.marker_map.get(record.diff_type, ("", ""))

        return f"{color}{marker}{self.term_control.NORMAL}"

    # pylint: disable=too-many-locals,too-many-branches
    def render(
        self,
        node: Optional[TreeNode] = None,
        desc: str = "none",
        prefix: str = "",
        is_last: bool = True,
    ) -> Optional[str]:
        """
        Recursively render tree with proper box-drawing characters.

        :param node: The node to begin rendering from.
        :type node: ``Optional[TreeNode]``
        :param desc: Include descriptions: "short" for brief description, "full"
                     for complete change descriptions or "none" to omit.
        :type desc: ``Optional[str]``
        :param prefix: The prefix string for this node.
        :type prefix: ``str``
        :param is_last: ``True`` if this node is the last child of its parent.
        :type is_last: ``bool``
        """
        node = node or self.root
        is_root = node == self.root
        if node is None:
            raise ValueError("Render node is undefined")

        if is_root:
            if self._rendered is None:
                self._rendered = []
            else:
                raise RuntimeError("Cannot restart rendering while render in progress")
        elif self._rendered is None:
            raise RuntimeError(
                "Cannot render a subtree before starting a root render()"
            )

        marker = self.get_change_marker(node.record, node)  # [+], [-], [*], etc.
        connector = "" if is_root else self.last if is_last else self.branch
        spacer = "" if not marker else " "

        if desc and desc != "none" and node.record:
            if desc == "full":
                change_descs = ", ".join(chg.description for chg in node.record.changes)
            else:
                change_descs = ", ".join(
                    chg.change_type.value for chg in node.record.changes
                )
            description = f" ({change_descs})" if change_descs else ""
        else:
            description = ""

        move = ""
        if node.record and node.record.diff_type == DiffType.MOVED:
            if node.to_or_from == "to":
                move = f" <- {node.record.moved_from}"
            else:
                move = f" -> {node.record.moved_to}"

        self._rendered.append(
            f"{prefix}{connector}{marker}{spacer}{node.name}{move}{description}"
        )

        # Calculate prefix for children
        extension = "" if is_root else "    " if is_last else f"{self.vbar}   "
        child_prefix = prefix + extension

        # Recurse to children
        children = sorted(node.children.values(), key=lambda n: n.name)
        for i, child in enumerate(children):
            child_is_last = i == len(children) - 1
            self.render(
                node=child, desc=desc, prefix=child_prefix, is_last=child_is_last
            )

        if node == self.root:
            rendered = "\n".join(self._rendered)
            self._rendered = None
            return rendered
        return None

    @staticmethod
    # pylint: disable=too-many-locals,too-many-statements
    def build_tree(
        results: "FsDiffResults",
        color: str = "auto",
        quiet: bool = False,
        term_control: Optional[TermControl] = None,
    ) -> "DiffTree":
        """
        Build a new ``DiffTree`` object from a ``"FsDiffResults"`` instance
        containing file system difference records.

        :param results: The file system diff results for this ``DiffTree`.
        :type results: ``"FsDiffResults"``
        :param color: A string to control color tree rendering: "auto",
                      "always", or "never".
        :type color: ``str``
        :param term_control: An optional ``TermControl`` instance to use for
                             formatting. The supplied instance overrides any
                             ``color`` argument if set.
        :type term_control: ``Optional[TermControl]``
        :returns: A new ``DiffTree`` instance reflecting ``results``.
        :rtype: ``DiffTree``
        """
        root = TreeNode(os.sep)
        orphan_moves = defaultdict(list)
        total_records = len(results)
        node_count = 0

        if total_records == 0:
            # No records: return an empty tree without invoking progress.
            return DiffTree(root, node_count, color=color, term_control=term_control)

        progress = ProgressFactory.get_progress(
            "Building DiffTree",
            quiet=quiet,
            term_control=term_control,
        )

        def _adopt_orphans(node: TreeNode, path: str):
            """
            Add orphaned move nodes to matching parent path.
            """
            _log_debug_fsdiff(
                "Checking adoption for %s (orphan_moves[%s]=%s)",
                path,
                path,
                orphan_moves.get(path, []),
            )
            # Re-parent orphaned moves if path matches
            if orphan_moves.get(path):
                for orphan in orphan_moves[path]:
                    _log_debug_fsdiff(
                        "Reparenting orphan move: %s to=%s",
                        orphan.name,
                        path,
                    )
                    node.children[orphan.name] = orphan

        def _reparent_all_orphans(parent: TreeNode, path: str):
            """
            Walk the tree and attach any remaining orphan moves to their
            proper parent directory.
            """
            _adopt_orphans(parent, path)
            for child_path, child in parent.children.items():
                _reparent_all_orphans(child, os.path.join(path, child_path))

        try:
            progress.start(total_records)
            for i, record in enumerate(results):
                # Treat a root-path record as belonging to the root node itself
                if record.path == os.sep:
                    _log_debug_fsdiff(
                        "Attaching root-path record to tree root: %s", record
                    )
                    root.record = record
                    continue

                path = record.path.strip(os.sep)
                parts = path.split(os.sep)

                _log_debug_fsdiff(
                    "Processing record with path: %s (parts=%s)",
                    record.path,
                    parts,
                )

                progress.progress(i, f"Processing {record.path}")

                node = root
                for part in parts[:-1]:
                    _log_debug_fsdiff("Processing path part: %s", part)
                    if part not in node.children:
                        _log_debug_fsdiff(
                            "Adding child to %s[%s] = TreeNode(%s)",
                            node.name,
                            part,
                            part,
                        )
                        node.children[part] = TreeNode(part)
                    node = node.children[part]

                # Optimistic pass
                parent_path = (
                    os.path.join(os.sep, *parts[:-1]) if parts[:-1] else os.sep
                )
                _adopt_orphans(node, parent_path)

                # Leaf node with actual record
                if record.diff_type != DiffType.MOVED:
                    _log_debug_fsdiff(
                        "Adding leaf node: %s, %s", parts[-1], record.diff_type.value
                    )
                    node.children[parts[-1]] = TreeNode(parts[-1], record)
                    node_count += 1
                else:
                    if not record.moved_from or not record.moved_to:
                        raise ValueError(
                            "MOVED record requires moved_from and moved_to"
                        )
                    # Create two nodes for a move
                    moved_from_parts = record.moved_from.strip(os.sep).split(os.sep)
                    moved_to_parts = record.moved_to.strip(os.sep).split(os.sep)
                    moved_from = moved_from_parts[-1]
                    moved_to = moved_to_parts[-1]

                    _log_debug_fsdiff(
                        "Adding leaf move nodes: %s (from=%s, to=%s)",
                        parts[-1],
                        moved_from,
                        moved_to,
                    )

                    node.children[moved_from] = TreeNode(
                        moved_from, record, to_or_from="from"
                    )
                    node_count += 1

                    # Rename within directory?
                    if moved_from_parts[:-1] == moved_to_parts[:-1]:
                        node.children[moved_to] = TreeNode(
                            moved_to, record, to_or_from="to"
                        )
                        node_count += 1
                    else:
                        orphan_path = os.path.join(os.sep, *moved_to_parts[:-1])
                        _log_debug_fsdiff(
                            "Adding orphan move: %s (%s)", moved_to, orphan_path
                        )
                        orphan_moves[orphan_path].append(
                            TreeNode(moved_to, record, to_or_from="to")
                        )
                        node_count += 1

            if orphan_moves:
                _log_debug_fsdiff("Processing orphan_moves=%s", orphan_moves)
                _reparent_all_orphans(root, "/")

        except KeyboardInterrupt:
            progress.cancel("Quit!")
            raise
        except SystemExit:
            progress.cancel("Exiting.")
            raise

        progress.end(f"Built tree with {node_count} nodes")

        return DiffTree(root, node_count, color=color, term_control=term_control)


__all__ = [
    "DiffTree",
]
