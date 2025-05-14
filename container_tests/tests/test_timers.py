import unittest
import logging
import os.path

import snapm
from snapm.manager._timers import (
    timer,
    TIMER_ENABLE,
    TIMER_DISABLE,
    TIMER_START,
    TIMER_STOP,
    UNIT_CREATE,
    UNIT_GC,
)
from snapm.manager._calendar import CalendarSpec

log = logging.getLogger(__name__)


class TimerTests(unittest.TestCase):
    def assert_paths(self, unit: str, instance: str, enabled: bool):
        unit_path = (
            f"/etc/systemd/system/timers.target.wants/snapm-{unit}@{instance}.timer"
        )
        drop_in_dir = f"/etc/systemd/system/snapm-{unit}@{instance}.timer.d"
        drop_in_file = os.path.join(drop_in_dir, "10-oncalendar.conf")

        self.assertEqual(enabled, os.path.exists(unit_path))
        self.assertEqual(enabled, os.path.exists(drop_in_dir))
        self.assertEqual(enabled, os.path.exists(drop_in_file))

    def enable_assert_disable_timer(self, unit: str, instance: str, calendarspec: str):
        timer(TIMER_ENABLE, unit, instance, calendarspec=CalendarSpec(calendarspec))
        self.assert_paths(unit, instance, True)

        timer(TIMER_START, unit, instance)
        # assert unit status

        timer(TIMER_STOP, unit, instance)
        # assert unit status

        timer(TIMER_DISABLE, unit, instance)
        self.assert_paths(unit, instance, False)

    def test_create_timer_enable_daily(self):
        self.enable_assert_disable_timer(UNIT_CREATE, "daily", "daily")

    def test_gc_timer_enable_daily(self):
        self.enable_assert_disable_timer(UNIT_GC, "daily", "daily")

    def test_create_timer_enable_hourly(self):
        self.enable_assert_disable_timer(UNIT_CREATE, "hourly", "hourly")

    def test_gc_timer_enable_hourly(self):
        self.enable_assert_disable_timer(UNIT_GC, "hourly", "hourly")

    def test_create_timer_enable_weekly(self):
        self.enable_assert_disable_timer(UNIT_CREATE, "weekly", "weekly")

    def test_gc_timer_enable_weekly(self):
        self.enable_assert_disable_timer(UNIT_GC, "weekly", "weekly")

    def test_create_timer_enable_monthly(self):
        self.enable_assert_disable_timer(UNIT_CREATE, "monthly", "monthly")

    def test_gc_timer_enable_monthly(self):
        self.enable_assert_disable_timer(UNIT_GC, "monthly", "monthly")

    def test_create_timer_enable_thu_fri_1_5_11(self):
        self.enable_assert_disable_timer(
            UNIT_CREATE, "thu_fri_1_5_11", "Thu,Fri *-*-1,5 11:12:13"
        )

    def test_gc_timer_enable_thu_fri_1_5_11(self):
        self.enable_assert_disable_timer(
            UNIT_GC, "thu_fri_1_5_11", "Thu,Fri *-*-1,5 11:12:13"
        )

    def test_create_timer_enable_sat_sun_8(self):
        self.enable_assert_disable_timer(UNIT_CREATE, "sat_sun_8", "Sat,Sun 08:05:40")

    def test_gc_timer_enable_sat_sun_8(self):
        self.enable_assert_disable_timer(UNIT_GC, "sat_sun_8", "Sat,Sun 08:05:40")

    def test_timer_enable_empty_calendarspec_raises(self):
        with self.assertRaises(snapm.SnapmArgumentError) as cm:
            timer(TIMER_ENABLE, UNIT_CREATE, "hourly", calendarspec="")
            self.assertTrue("requires non-empty calendarspec" in cm.exception)

    def test_timer_enable_bad_calendarspec_raises(self):
        with self.assertRaises(snapm.SnapmArgumentError) as cm:
            timer(TIMER_ENABLE, UNIT_CREATE, "hourly", calendarspec="quux:foo")
            self.assertTrue("invalid calendarspec string" in cm.exception)

    def test_timer_bad_op_raises(self):
        with self.assertRaises(snapm.SnapmArgumentError) as cm:
            timer("QUUX", UNIT_CREATE, "hourly", calendarspec="hourly")
            self.assertTrue("Invalid timer operation: QUUX" in cm.exception)

    def test_timer_bad_unit_raises(self):
        with self.assertRaises(snapm.SnapmArgumentError) as cm:
            timer(TIMER_ENABLE, "quux", "hourly", calendarspec="hourly")
            self.assertTrue("Invalid timer unit" in cm.exception)

    def test_timer_empty_instance_raises(self):
        with self.assertRaises(snapm.SnapmArgumentError) as cm:
            timer(TIMER_ENABLE, UNIT_CREATE, "", calendarspec="hourly")
            self.assertTrue("Timer instance cannot be empty" in cm.exception)

    def test_timer_none_instance_raises(self):
        with self.assertRaises(snapm.SnapmArgumentError) as cm:
            timer(TIMER_ENABLE, UNIT_CREATE, None, calendarspec="hourly")
            self.assertTrue("Timer instance cannot be empty" in cm.exception)

    def test_timer_bad_op_with_calendarspec_raises(self):
        with self.assertRaises(snapm.SnapmArgumentError) as cm:
            timer(TIMER_START, UNIT_CREATE, "hourly", calendarspec="hourly")
            self.assertTrue("does not accept calendarspec" in cm.exception)

        with self.assertRaises(snapm.SnapmArgumentError) as cm:
            timer(TIMER_STOP, UNIT_CREATE, "hourly", calendarspec="hourly")
            self.assertTrue("does not accept calendarspec" in cm.exception)

        with self.assertRaises(snapm.SnapmArgumentError) as cm:
            timer(TIMER_DISABLE, UNIT_CREATE, "hourly", calendarspec="hourly")
            self.assertTrue("does not accept calendarspec" in cm.exception)
