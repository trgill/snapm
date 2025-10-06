# Copyright Red Hat
#
# tests/test_manager.py - Manager core unit tests
#
# This file is part of the snapm project.
#
# SPDX-License-Identifier: Apache-2.0
import unittest
import logging
import os
from os.path import exists, join
from json import loads
from uuid import UUID


import snapm
import snapm.manager as manager
from snapm.manager._schedule import GcPolicyType, GcPolicyParams
import boom

from tests import have_root, BOOT_ROOT_TEST
from ._util import LvmLoopBacked, StratisLoopBacked


log = logging.getLogger()

boom.set_boot_path(BOOT_ROOT_TEST)

_ETC_SNAPM_SCHEDULE_D = "/etc/snapm/schedule.d"

sched_json = """{
    "name": "hourly",
    "sources": [
        "%s",
        "%s"
    ],
    "default_size_policy": "25%%SIZE",
    "autoindex": true,
    "calendarspec": "hourly",
    "boot": false,
    "revert": false,
    "gc_policy": {
        "policy_name": "hourly",
        "policy_type": "COUNT",
        "keep_count": 2
    }
}"""


@unittest.skipIf(not have_root(), "requires root privileges")
class SchedulerTests(unittest.TestCase):
    """
    Tests for snapm.manager.Manager.Scheduler that apply to all supported
    snapshot providers.
    """
    volumes = ["root", "var"]
    thin_volumes = ["opt", "srv", "thin-vol"]
    stratis_volumes = ["fs1", "fs2"]

    def setUp(self):
        log.debug("Preparing %s", self._testMethodName)
        def cleanup_lvm():
            log.debug("Cleaning up LVM (%s)", self._testMethodName)
            if hasattr(self, "_lvm"):
                self._lvm.destroy()

        def cleanup_stratis():
            log.debug("Cleaning up Stratis (%s)", self._testMethodName)
            if hasattr(self, "_stratis"):
                self._stratis.destroy()

        self.addCleanup(cleanup_lvm)
        self.addCleanup(cleanup_stratis)

        self._lvm = LvmLoopBacked(self.volumes, thin_volumes=self.thin_volumes)
        self._stratis = StratisLoopBacked(self.stratis_volumes)

        self.manager = None

    def mount_points(self):
        return self._lvm.mount_points() + self._stratis.mount_points()

    def test_load_and_find_schedules(self):
        mount_points = self.mount_points()
        with open(join(_ETC_SNAPM_SCHEDULE_D, "hourly.json"), "w", encoding="utf8") as fp:
            fp.write(sched_json % (mount_points[0], mount_points[1]))

        self.manager = manager.Manager()
        schedule = self.manager.scheduler.find_schedules(snapm.Selection(sched_name="hourly"))[0]
        self.assertEqual(schedule.name, "hourly")
        self.assertEqual(schedule.sources[0], mount_points[0])
        self.assertEqual(schedule.sources[1], mount_points[1])
        self.assertEqual(schedule.default_size_policy, "25%SIZE")
        self.assertEqual(schedule.autoindex, True)
        self.assertEqual(schedule.calendarspec, "hourly")
        self.assertEqual(schedule.boot, False)
        self.assertEqual(schedule.revert, False)
        self.assertEqual(schedule.gc_policy.name, "hourly")
        self.assertEqual(schedule.gc_policy.type, GcPolicyType.COUNT)
        self.assertEqual(schedule.gc_policy.params.to_dict(), {"keep_count": 2})

    def test_schedule_create_ALL(self):
        self.manager = manager.Manager()
        schedule = self.manager.scheduler.create(
            "weekly",
            self.mount_points(),
            "10%SIZE",
            True,
            "weekly",
            manager.GcPolicy("weekly", manager.GcPolicyType.ALL, {}),
            False,
            False,
        )
        sched_file = join(_ETC_SNAPM_SCHEDULE_D, "weekly.json")
        self.assertTrue(exists(sched_file))
        sched_json = ""
        with open(sched_file, "r", encoding="utf8") as fp:
            sched_json = fp.read()
        self.assertEqual(schedule.json(pretty=True), sched_json)

        self.manager.scheduler.delete("weekly")

    def test_schedule_create_COUNT(self):
        self.manager = manager.Manager()
        schedule = self.manager.scheduler.create(
            "weekly",
            self.mount_points(),
            "10%SIZE",
            True,
            "weekly",
            manager.GcPolicy("weekly", manager.GcPolicyType.COUNT, {"keep_count": 2}),
            False,
            False,
        )
        sched_file = join(_ETC_SNAPM_SCHEDULE_D, "weekly.json")
        self.assertTrue(exists(sched_file))
        sched_json = ""
        with open(sched_file, "r", encoding="utf8") as fp:
            sched_json = fp.read()
        self.assertEqual(schedule.json(pretty=True), sched_json)

        self.manager.scheduler.delete("weekly")

    def test_schedule_create_AGE(self):
        self.manager = manager.Manager()
        schedule = self.manager.scheduler.create(
            "weekly",
            self.mount_points(),
            "10%SIZE",
            True,
            "weekly",
            manager.GcPolicy("weekly", manager.GcPolicyType.AGE, {"keep_days": 7}),
            False,
            False,
        )
        sched_file = join(_ETC_SNAPM_SCHEDULE_D, "weekly.json")
        self.assertTrue(exists(sched_file))
        sched_json = ""
        with open(sched_file, "r", encoding="utf8") as fp:
            sched_json = fp.read()
        self.assertEqual(schedule.json(pretty=True), sched_json)

        self.manager.scheduler.delete("weekly")

    def test_schedule_create_TIMELINE(self):
        self.manager = manager.Manager()
        schedule = self.manager.scheduler.create(
            "weekly",
            self.mount_points(),
            "10%SIZE",
            True,
            "weekly",
            manager.GcPolicy("weekly", manager.GcPolicyType.TIMELINE, {"keep_daily": 7}),
            False,
            False,
        )
        sched_file = join(_ETC_SNAPM_SCHEDULE_D, "weekly.json")
        self.assertTrue(exists(sched_file))
        sched_json = ""
        with open(sched_file, "r", encoding="utf8") as fp:
            sched_json = fp.read()
        self.assertEqual(schedule.json(pretty=True), sched_json)

        self.manager.scheduler.delete("weekly")

    def test_schedule_create_duplicate_sources_raises(self):
        self.manager = manager.Manager()
        with self.assertRaises(snapm.SnapmInvalidIdentifierError):
            self.manager.scheduler.create(
                "weekly",
                [self.mount_points()[0], self.mount_points()[0]],
                "10%SIZE",
                True,
                "weekly",
                manager.GcPolicy("weekly", manager.GcPolicyType.ALL, {}),
                False,
                False,
            )

    def test_schedule_delete(self):
        mount_points = self.mount_points()
        sched_file = join(_ETC_SNAPM_SCHEDULE_D, "hourly.json")
        with open(sched_file, "w", encoding="utf8") as fp:
            fp.write(sched_json % (mount_points[0], mount_points[1]))

        self.manager = manager.Manager()

        self.assertTrue(exists(sched_file))
        self.manager.scheduler.delete("hourly")
        self.assertFalse(exists(sched_file))

    def test_schedule_enable(self):
        mount_points = self.mount_points()
        sched_file = join(_ETC_SNAPM_SCHEDULE_D, "hourly.json")
        with open(sched_file, "w", encoding="utf8") as fp:
            fp.write(sched_json % (mount_points[0], mount_points[1]))

        self.manager = manager.Manager()

        schedule = self.manager.scheduler.find_schedules(snapm.Selection(sched_name="hourly"))[0]

        self.assertFalse(schedule.enabled)
        self.manager.scheduler.enable("hourly", True)
        self.assertTrue(schedule.enabled)

        self.manager.scheduler.delete("hourly")

    def test_schedule_disable(self):
        mount_points = self.mount_points()
        sched_file = join(_ETC_SNAPM_SCHEDULE_D, "hourly.json")
        with open(sched_file, "w", encoding="utf8") as fp:
            fp.write(sched_json % (mount_points[0], mount_points[1]))

        self.manager = manager.Manager()

        schedule = self.manager.scheduler.find_schedules(snapm.Selection(sched_name="hourly"))[0]
        self.manager.scheduler.enable("hourly", True)

        self.assertTrue(schedule.enabled)
        self.manager.scheduler.disable("hourly")
        self.assertFalse(schedule.enabled)

        self.manager.scheduler.delete("hourly")

    def test_schedule_start(self):
        mount_points = self.mount_points()
        sched_file = join(_ETC_SNAPM_SCHEDULE_D, "hourly.json")
        with open(sched_file, "w", encoding="utf8") as fp:
            fp.write(sched_json % (mount_points[0], mount_points[1]))

        self.manager = manager.Manager()

        schedule = self.manager.scheduler.find_schedules(snapm.Selection(sched_name="hourly"))[0]
        self.manager.scheduler.enable("hourly", False)

        self.assertTrue(schedule.enabled)
        self.assertFalse(schedule.running)
        self.manager.scheduler.start("hourly")
        self.assertTrue(schedule.enabled)
        self.assertTrue(schedule.running)

        self.manager.scheduler.delete("hourly")


    def test_schedule_stop(self):
        mount_points = self.mount_points()
        sched_file = join(_ETC_SNAPM_SCHEDULE_D, "hourly.json")
        with open(sched_file, "w", encoding="utf8") as fp:
            fp.write(sched_json % (mount_points[0], mount_points[1]))

        self.manager = manager.Manager()

        schedule = self.manager.scheduler.find_schedules(snapm.Selection(sched_name="hourly"))[0]
        self.manager.scheduler.enable("hourly", True)

        self.assertTrue(schedule.enabled)
        self.assertTrue(schedule.running)
        self.manager.scheduler.stop("hourly")
        self.assertTrue(schedule.enabled)
        self.assertFalse(schedule.running)

        self.manager.scheduler.delete("hourly")


    def test_schedule_gc(self):
        mount_points = self.mount_points()
        sched_file = join(_ETC_SNAPM_SCHEDULE_D, "hourly.json")
        with open(sched_file, "w", encoding="utf8") as fp:
            fp.write(sched_json % (mount_points[0], mount_points[1]))

        self.manager = manager.Manager()

        self.manager.scheduler.gc("hourly")
        self.manager.scheduler.delete("hourly")

    def test_delete_schedule_nosuch_raises(self):
        self.manager = manager.Manager()
        with self.assertRaises(snapm.SnapmNotFoundError) as cm:
            self.manager.scheduler.delete("nosuch")
