# Copyright Red Hat
#
# snapm/_fsdiff/options.py - Snapshot Manager fs diff options
#
# This file is part of the snapm project.
#
# SPDX-License-Identifier: Apache-2.0
"""
File system diff options and categories.
"""
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


@dataclass
class DiffOptions:
    """
    File system comparison options.
    """

    #: Ignore timestamps in diff comparisons
    ignore_timestamps: bool = False
    #: Ignore permissions in diff comparisons
    ignore_permissions: bool = False
    #: Ignore ownership in diff comparisons
    ignore_ownership: bool = False
    #: Only consider content changes
    content_only: bool = False
    #: Include system directories in diff comparisons (unimplemented)
    include_system_dirs: bool = True
    #: Generate content diffs for detected file modifications
    include_content_diffs: bool = True
    #: Generate file type information using magic
    include_file_type: bool = True
    #: Follow symlinks when walking file system trees
    follow_symlinks: bool = False
    #: Maximum file size for diff comparisons
    max_file_size: int = 0
    #: Maximum size for generating content diffs
    max_content_diff_size: int = 2**20
    #: Maximum file size for generating content hashes
    max_content_hash_size: int = 2**20
    #: File patterns to include (glob notation)
    file_patterns: List[str] = field(default_factory=list)
    #: File patterns to exclude (glob notation)
    exclude_patterns: List[str] = field(default_factory=list)
    #: Start path for file system comparison
    from_path: Optional[str] = None

    def __str__(self):
        """
        Return a human readable string representation of this
        ``DiffOptions`` instance.

        :returns: A human readable string.
        :rtype: ``str``
        """

        def _join_list(val: List[str]) -> str:
            """
            Convert string lists into space separated strings.

            :param val: The value to join.
            :type val: ``List[str]``
            :returns: The string list value converted to a space separated
                      string.
            :rtype: ``str``
            """
            return " ".join(val)

        items = [
            (key, val) if not isinstance(val, list) else (key, _join_list(val))
            for key, val in self.__dict__.items()
        ]
        return "\n".join(f"{key}={val}" for key, val in items)


class DiffCategories(Enum):
    """
    Enum for categories of difference based on type or file system location.
    """

    CRITICAL_SYSTEM = "critical_system"  # /etc, /boot changes
    USER_DATA = "user_data"  # /home changes
    APPLICATION = "application"  # /usr, /opt changes
    TEMPORARY = "temporary"  # /tmp, /var/tmp
    LOG_FILES = "log_files"  # /var/log changes
    PACKAGE_MANAGEMENT = "package_mgmt"  # Package-related changes
