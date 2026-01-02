#!/usr/bin/python3
# Copyright Red Hat
#
# difftest.py - simple example driver for snapm.fsdiff
#
# This file is part of the snapm project.
#
# SPDX-License-Identifier: Apache-2.0
from argparse import ArgumentParser
import logging
import sys

import snapm
import snapm.manager
import snapm.manager.plugins

from snapm.fsdiff import FsDiffer, DiffOptions

LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARNING,
    "error": logging.ERROR,
}

def main():
    parser = ArgumentParser(prog="difftest.py")
    parser.add_argument(
        "-f",
        "--file-types",
        dest="use_magic_file_type",
        help="Generate file type information (slower)",
        action="store_true",
    )
    parser.add_argument(
        "-l",
        "--log-level",
        default="info",
        help=f"Set log level ({', '.join(LOG_LEVELS.keys())})",
        choices=LOG_LEVELS.keys(),
    )
    parser.add_argument(
        "-n",
        "--no-content-diffs",
        dest="include_content_diffs",
        help="Do not generate content diffs",
        action="store_false",
    )
    parser.add_argument(
        "-s",
        "--start-path",
        type=str,
        action="append",
        metavar="PATH",
        dest="from_path",
        default=None,
        help="Start traversal from PATH",
    )
    parser.add_argument(
        "diff_from",
        type=str,
        help="Snapshot set name to compare to system",
    )
    args = parser.parse_args()
    args.diff_to = "."
    snapm_log = logging.getLogger("snapm")
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    snapm_log.setLevel(LOG_LEVELS[args.log_level])
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    snapm_log.addHandler(console_handler)
    m = snapm.manager.Manager()
    sys_root = m.mounts.get_sys_mount()
    did_mount = False
    mounts = m.mounts.find_mounts(snapm.Selection(name=args.diff_from))
    if not mounts:
        snapsets = m.find_snapshot_sets(snapm.Selection(name=args.diff_from))
        if not snapsets:
            print(f"Cannot find snapshot set named '{args.diff_from}'", file=sys.stderr)
            sys.exit(1)
        snapset = snapsets[0]
        snap_root = m.mounts.mount(snapset)
        did_mount = True
    else:
        snap_root = mounts[0]

    options = DiffOptions.from_cmd_args(args)

    fsd = FsDiffer(m, options=options)
    try:
        results = fsd.compare_roots(snap_root, sys_root)
        print(f"Found {len(results)} changes:")
        print("\n\n".join(str(record) for record in results))
    except (KeyboardInterrupt, BrokenPipeError):
        # Graceful early exit on user abort or broken pipe
        return
    except SystemExit:
        # Preserve non-zero exit statuses from deeper layers
        raise
    finally:
        if did_mount:
            m.mounts.umount(snapset)

if __name__ == "__main__":
    main()
