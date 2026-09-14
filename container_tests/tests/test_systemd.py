import unittest
import logging
import os
import os.path

from snapm.manager._systemd import (
    UnitStatus,
    _enable_unit,
    _start_unit,
    _stop_unit,
    _disable_unit,
    _unit_status,
)
from snapm.manager._timers import (
    TimerStatus,
    _UNIT_FORMATS,
    _UNIT_CREATE,
    _UNIT_GC,
    _write_drop_in,
    _remove_drop_in,
)
from snapm.manager._calendar import CalendarSpec

log = logging.getLogger(__name__)

_ETC_SYSTEMD_SYSTEM = "/etc/systemd/system"
_DROP_IN_DIR_FMT = f"{_ETC_SYSTEMD_SYSTEM}/%s.d"
_10_ON_CALENDAR_CONF = "10-oncalendar.conf"


class UnitStatusTests(unittest.TestCase):
    """
    Tests for the UnitStatus enum.
    """

    def test_UnitStatus_values(self):
        """
        Verify UnitStatus enum has all expected members.
        """
        self.assertEqual(UnitStatus.DISABLED.value, "disable")
        self.assertEqual(UnitStatus.ENABLED.value, "enabled")
        self.assertEqual(UnitStatus.RUNNING.value, "running")
        self.assertEqual(UnitStatus.STOPPED.value, "stopped")
        self.assertEqual(UnitStatus.INVALID.value, "invalid")

    def test_UnitStatus_TimerStatus_parity(self):
        """
        Verify UnitStatus and TimerStatus have matching member values.
        """
        for member in UnitStatus:
            self.assertIn(
                member.name, TimerStatus.__members__,
                f"UnitStatus.{member.name} has no TimerStatus counterpart"
            )
            self.assertEqual(
                member.value, TimerStatus[member.name].value,
                f"UnitStatus.{member.name} value mismatch with TimerStatus"
            )


class SystemdUnitTests(unittest.TestCase):
    """
    Tests for the general systemd unit management functions. Uses the
    snapm timer template units as the test subject, handling drop-in
    file management directly to prove decoupling from _timers.
    """

    def _setup_drop_in(self, unit_name, calendarspec_str):
        """
        Write a timer drop-in file for the given unit.
        """
        drop_in_dir = _DROP_IN_DIR_FMT % unit_name
        drop_in_file = os.path.join(drop_in_dir, _10_ON_CALENDAR_CONF)
        calendarspec = CalendarSpec(calendarspec_str)
        _write_drop_in(drop_in_dir, drop_in_file, calendarspec)
        return drop_in_dir, drop_in_file

    def _cleanup_drop_in(self, drop_in_dir, drop_in_file):
        """
        Remove a timer drop-in file and directory.
        """
        _remove_drop_in(drop_in_dir, drop_in_file)

    def _unit_enable_start_stop_disable(self, unit_type, instance, calendarspec):
        """
        Exercise the full lifecycle of a unit using the general systemd
        functions directly.
        """
        unit_name = _UNIT_FORMATS[unit_type] % instance
        drop_in_dir, drop_in_file = self._setup_drop_in(unit_name, calendarspec)
        enabled = False

        try:
            # Verify unit starts as disabled
            self.assertEqual(_unit_status(unit_name), UnitStatus.DISABLED)

            # Enable and verify
            _enable_unit(unit_name)
            enabled = True
            self.assertEqual(_unit_status(unit_name), UnitStatus.ENABLED)

            # Start and verify
            _start_unit(unit_name)
            self.assertEqual(_unit_status(unit_name), UnitStatus.RUNNING)

            # Stop and verify
            _stop_unit(unit_name)
            self.assertEqual(_unit_status(unit_name), UnitStatus.ENABLED)

            # Disable and verify
            _disable_unit(unit_name)
            enabled = False
            self.assertEqual(_unit_status(unit_name), UnitStatus.DISABLED)
        finally:
            try:
                if enabled:
                    _disable_unit(unit_name)
            finally:
                self._cleanup_drop_in(drop_in_dir, drop_in_file)

    def test_create_unit_lifecycle_hourly(self):
        """
        Test full unit lifecycle using the create timer template with
        an hourly calendar spec.
        """
        self._unit_enable_start_stop_disable(_UNIT_CREATE, "hourly", "hourly")

    def test_gc_unit_lifecycle_hourly(self):
        """
        Test full unit lifecycle using the gc timer template with
        an hourly calendar spec.
        """
        self._unit_enable_start_stop_disable(_UNIT_GC, "hourly", "hourly")

    def test_create_unit_lifecycle_daily(self):
        """
        Test full unit lifecycle using the create timer template with
        a daily calendar spec.
        """
        self._unit_enable_start_stop_disable(_UNIT_CREATE, "daily", "daily")

    def test_gc_unit_lifecycle_daily(self):
        """
        Test full unit lifecycle using the gc timer template with
        a daily calendar spec.
        """
        self._unit_enable_start_stop_disable(_UNIT_GC, "daily", "daily")

    def test_unit_status_nonexistent_unit(self):
        """
        Verify that querying status of a non-existent unit returns
        UnitStatus.DISABLED.
        """
        status = _unit_status("snapm-create@nonexistent.timer")
        self.assertEqual(status, UnitStatus.DISABLED)
