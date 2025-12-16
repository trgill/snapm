#!/usr/bin/python3
# Copyright Red Hat
#
# progtest.py - simple demo of snapm.progress
#
# This file is part of the snapm project.
#
# SPDX-License-Identifier: Apache-2.0
from argparse import ArgumentParser
from random import randrange
import time
import os

from snapm.progress import ProgressFactory, TermControl, Throbber

path_bits = (
    "bin",
    "etc",
    "mnt",
    "usr",
    "share",
    "lib",
    "lib64",
    "var",
    "cache",
    "home",
    "opt",
    "srv",
    "stuff",
    "things",
    "quux",
    "foo",
    "bar",
    "baz",
)

def rand_path():
    path_len = randrange(10)
    path = "/"
    for _ in range(0, path_len):
        path = os.path.join(path, path_bits[randrange(len(path_bits))])
    return path

def main():
    tc = TermControl()

    parser = ArgumentParser("progtest.py")
    parser.add_argument(
        "-c",
        "--colors",
        help="Print color test",
        action="store_true",
    )
    parser.add_argument(
        "-t",
        "--throb",
        help="Demo throbbers",
        action="store_true",
    )
    parser.add_argument(
        "-p",
        "--progress",
        help="Demo progress bars",
        action="store_true",
    )
    parser.add_argument(
        "-n",
        "--no-clear",
        help="Pass no_clear=True to progress bars and throbbers",
        action="store_true",
    )
    parser.add_argument(
        "-s",
        "--style",
        help=f"Select throbber style ({','.join(Throbber.STYLES.keys())})",
        type=str,
        choices=Throbber.STYLES.keys(),
    )
    parser.add_argument(
        "-f",
        "--high-frequency",
        help="Simulate high frequency updates with many work items",
        action="store_true",
    )
    parser.add_argument(
        "-l",
        "--long-message",
        help="Generate long random progress messages",
        action="store_true",
    )

    args = parser.parse_args()

    p_interval = 0.3 if not args.high_frequency else 0.000001
    t_interval = 0.01 if not args.high_frequency else 0.0001

    if args.colors:
        print("This is " + tc.BLUE + "BLUE" + tc.NORMAL + " text")
        print("This is " + tc.GREEN + "GREEN" + tc.NORMAL + " text")
        print("This is " + tc.CYAN + "CYAN" + tc.NORMAL + " text")
        print("This is " + tc.RED + "RED" + tc.NORMAL + " text")
        print("This is " + tc.MAGENTA + "MAGENTA" + tc.NORMAL + " text")
        print("This is " + tc.YELLOW + "YELLOW" + tc.NORMAL + " text")
        print("This is " + tc.WHITE + "WHITE" + tc.NORMAL + " text")

    if args.progress:
        progress = ProgressFactory.get_progress("Doing Something", no_clear=args.no_clear)
        try:
            jobs = ["This", "That", "Other", "Foo", "Bar", "Baz", "Quux"]
            if args.high_frequency:
                jobs = jobs * 10000
            progress.start(len(jobs))
            for i, job in enumerate(jobs):
                the_job = job if not args.long_message else os.path.join(rand_path(), job)
                progress.progress(i, f"Working on {the_job}")
                time.sleep(p_interval)
            progress.end("All done!")
        except KeyboardInterrupt:
            progress.cancel("Quit!")
            return

        progress = ProgressFactory.get_progress("Doing Something Broken", no_clear=args.no_clear)
        try:
            jobs.reverse()
            progress.start(len(jobs))
            for i, job in enumerate(jobs):
                the_job = job if not args.long_message else os.path.join(rand_path(), job)
                progress.progress(i, f"Working on {the_job}")
                time.sleep(p_interval)
                if i > (len(jobs) // 4):
                    progress.cancel("OH NOES!")
                    break
        except KeyboardInterrupt:
            progress.cancel("Quit!")
            return

    if args.throb:
        throbber = ProgressFactory.get_throbber(
            f"Doing Something Unbounded with quit ({args.style or 'default'})",
            style=args.style,
            no_clear=args.no_clear,
        )
        try:
            jobs = [f"job{i}" for i in range(0, 500 if not args.high_frequency else 500000)]
            throbber.start()
            for _ in jobs:
                throbber.throb()
                time.sleep(t_interval)
            throbber.end()
        except KeyboardInterrupt:
            throbber.end("Quit!")

        throbber = ProgressFactory.get_throbber(
            f"Doing Something Unbounded with interrupt ({args.style or 'default'})",
            style=args.style,
            no_clear=args.no_clear,
        )
        try:
            jobs = [f"job{i}" for i in range(0, 500 if not args.high_frequency else 500000)]
            throbber.start()
            for i, _ in enumerate(jobs):
                throbber.throb()
                time.sleep(t_interval)
                if i > (250 if not args.high_frequency else 250000):
                    raise KeyboardInterrupt
            throbber.end()
        except KeyboardInterrupt:
            throbber.end("Quit!")


if __name__ == "__main__":
    main()
