# Copyright Red Hat
#
# virt_tests/util.py - Snapshot Manager virt_tests utilities.
#
# This file is part of the snapm project.
#
# SPDX-License-Identifier: Apache-2.0
"""
Utilities for snapm virt-tests
"""
import sys


def log_print(*args, **kwargs):
    kwargs.setdefault("flush", True)
    print(*args, **kwargs)


def err_print(*args, **kwargs):
    kwargs.setdefault("flush", True)
    kwargs.setdefault("file", sys.stderr)
    print(*args, **kwargs)


__all__ = ["log_print", "err_print"]
