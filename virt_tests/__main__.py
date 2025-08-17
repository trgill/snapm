# Copyright Red Hat
#
# virt_tests/__main__.py - Snapshot Manager virt_tests CLI driver.
#
# This file is part of the snapm project.
#
# SPDX-License-Identifier: Apache-2.0
"""
CLI interface for snapm end-to-end testing framework.
"""
from argparse import ArgumentParser
import random
import string
import sys
import os

from .strategy import run_e2e_test
from .testvm import STORAGE_LAYOUTS

if __name__ == "__main__":

    parser = ArgumentParser(description="snapm virt tests", prog="virt_tests")

    parser.add_argument(
        "--allow-root",
        action="store_true",
        help="Enable VM root account access",
    )
    parser.add_argument(
        "base_os",
        metavar="BASE_OS",
        type=str,
        help="Operating system to install",
    )
    parser.add_argument(
        "--repo",
        metavar="REPOSITORY",
        default=os.environ.get("REPOSITORY", "snapshotmanager/snapm"),
        type=str,
        help="Repository under test (default: $REPOSITORY or snapshotmanager/snapm)",
    )
    parser.add_argument(
        "--ref-name",
        metavar="REF_NAME",
        default=os.environ.get("REF_NAME", "main"),
        type=str,
        help="Ref under test (default: $REF_NAME or main)",
    )
    parser.add_argument(
        "--storage",
        "-s",
        type=str,
        default="lvm",
        help="Storage layout",
        choices=STORAGE_LAYOUTS.keys(),
    )
    firmware_group = parser.add_mutually_exclusive_group()
    firmware_group.add_argument(
        "--uefi",
        action="store_true",
        default=False,
        help="Use UEFI boot firmware",
    )
    firmware_group.add_argument(
        "--bios",
        action="store_false",
        dest="uefi",
        help="Use BIOS boot firmware (default)",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        default=False,
        help="Keep VM running at end of test",
    )

    args = parser.parse_args()

    base_os = args.base_os
    storage = args.storage
    vm_uefi = args.uefi
    vm_keep = args.keep
    allow_root = args.allow_root
    repo = args.repo
    ref_name = args.ref_name

    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=5))
    vm_name = f"snapm-test-{base_os}-{os.getpid()}-{rand}"

    success = run_e2e_test(
        vm_name,
        base_os=base_os,
        storage=storage,
        uefi=vm_uefi,
        allow_root=allow_root,
        keep=vm_keep,
        repo=repo,
        ref_name=ref_name,
    )

    sys.exit(0 if success else 1)
