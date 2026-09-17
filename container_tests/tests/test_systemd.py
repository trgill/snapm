import unittest
import logging
import os
import os.path
from unittest.mock import patch
from subprocess import run

from snapm.manager._systemd import (
    UnitStatus,
    enable_unit,
    start_unit,
    stop_unit,
    disable_unit,
    unit_status,
    sort_units,
    _unit_dependencies,
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
            self.assertEqual(unit_status(unit_name), UnitStatus.DISABLED)

            # Enable and verify
            enable_unit(unit_name)
            enabled = True
            self.assertEqual(unit_status(unit_name), UnitStatus.ENABLED)

            # Start and verify
            start_unit(unit_name)
            self.assertEqual(unit_status(unit_name), UnitStatus.RUNNING)

            # Stop and verify
            stop_unit(unit_name)
            self.assertEqual(unit_status(unit_name), UnitStatus.ENABLED)

            # Disable and verify
            disable_unit(unit_name)
            enabled = False
            self.assertEqual(unit_status(unit_name), UnitStatus.DISABLED)
        finally:
            try:
                if enabled:
                    disable_unit(unit_name)
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
        status = unit_status("snapm-create@nonexistent.timer")
        self.assertEqual(status, UnitStatus.DISABLED)


class SortUnitsTests(unittest.TestCase):
    """
    Tests for the unit dependency sort using synthetic dependency data.

    Dependencies are expressed as a map from unit name to a two-tuple of
    the units that the unit depends upon, and the units that depend upon
    the unit, mirroring the return value of ``_unit_dependencies()``.
    """

    def sort_units_with_deps(self, unit_names, deps):
        """
        Sort ``unit_names`` with ``_unit_dependencies()`` patched to return
        the dependencies given by the ``deps`` map.
        """

        def fake_dependencies(unit_name):
            (depends, depended) = deps.get(unit_name, ((), ()))
            return (set(depends), set(depended))

        with patch(
            "snapm.manager._systemd._unit_dependencies", side_effect=fake_dependencies
        ):
            return sort_units(unit_names)

    def test_sort_units_empty_list(self):
        """
        Verify that sorting an empty list returns an empty list.
        """
        self.assertEqual(self.sort_units_with_deps([], {}), [])

    def test_sort_units_single_unit(self):
        """
        Verify that sorting a single unit returns that unit.
        """
        self.assertEqual(self.sort_units_with_deps(["a.timer"], {}), ["a.timer"])

    def test_sort_units_no_dependencies_preserves_order(self):
        """
        Verify that units with no dependency relationship retain their
        relative order.
        """
        units = ["c.timer", "a.timer", "b.timer"]
        self.assertEqual(self.sort_units_with_deps(units, {}), units)

    def test_sort_units_after_stops_dependent_first(self):
        """
        Verify that a unit ordered After another unit is stopped first.
        """
        deps = {"a.timer": (("b.timer",), ())}
        self.assertEqual(
            self.sort_units_with_deps(["b.timer", "a.timer"], deps),
            ["a.timer", "b.timer"],
        )

    def test_sort_units_before_stops_dependent_first(self):
        """
        Verify that a unit ordered Before another unit is stopped last.
        """
        deps = {"a.timer": ((), ("b.timer",))}
        self.assertEqual(
            self.sort_units_with_deps(["a.timer", "b.timer"], deps),
            ["b.timer", "a.timer"],
        )

    def test_sort_units_chain(self):
        """
        Verify that a chain of dependencies is sorted from the most
        dependent unit to the least dependent unit.
        """
        deps = {
            "a.timer": (("b.timer",), ()),
            "b.timer": (("c.timer",), ()),
        }
        self.assertEqual(
            self.sort_units_with_deps(["c.timer", "b.timer", "a.timer"], deps),
            ["a.timer", "b.timer", "c.timer"],
        )

    def test_sort_units_diamond(self):
        """
        Verify that a diamond shaped dependency graph is sorted with the
        dependent units before the units that they depend upon.
        """
        deps = {
            "a.timer": (("b.timer", "c.timer"), ()),
            "b.timer": (("d.timer",), ()),
            "c.timer": (("d.timer",), ()),
        }
        units = ["d.timer", "c.timer", "b.timer", "a.timer"]
        ordered = self.sort_units_with_deps(units, deps)
        self.assertEqual(ordered[0], "a.timer")
        self.assertEqual(ordered[-1], "d.timer")
        self.assertEqual(set(ordered), set(units))

    def test_sort_units_mixed_before_and_after(self):
        """
        Verify that Before and After dependencies describing the same
        ordering are sorted consistently.
        """
        deps = {
            "a.timer": (("b.timer",), ()),
            "b.timer": ((), ("a.timer",)),
        }
        self.assertEqual(
            self.sort_units_with_deps(["b.timer", "a.timer"], deps),
            ["a.timer", "b.timer"],
        )

    def test_sort_units_external_dependencies_ignored(self):
        """
        Verify that dependencies on units that are not members of the list
        do not affect the sort.
        """
        deps = {
            "a.timer": (("sysinit.target",), ("shutdown.target",)),
            "b.timer": (("basic.target",), ()),
        }
        self.assertEqual(
            self.sort_units_with_deps(["a.timer", "b.timer"], deps),
            ["a.timer", "b.timer"],
        )

    def test_sort_units_duplicates_removed(self):
        """
        Verify that duplicate unit names are removed from the sorted list.
        """
        deps = {"a.timer": (("b.timer",), ())}
        self.assertEqual(
            self.sort_units_with_deps(["b.timer", "a.timer", "b.timer"], deps),
            ["a.timer", "b.timer"],
        )

    def test_sort_units_self_dependency_ignored(self):
        """
        Verify that a unit that depends upon itself does not deadlock the
        sort.
        """
        deps = {"a.timer": (("a.timer",), ("a.timer",))}
        self.assertEqual(
            self.sort_units_with_deps(["a.timer", "b.timer"], deps),
            ["a.timer", "b.timer"],
        )

    def test_sort_units_dependency_loop_is_broken(self):
        """
        Verify that a dependency loop is broken in list order and that a
        warning is logged.
        """
        deps = {
            "a.timer": (("b.timer",), ()),
            "b.timer": (("a.timer",), ()),
        }
        with self.assertLogs("snapm.manager._systemd", level="WARNING") as cm:
            ordered = self.sort_units_with_deps(["b.timer", "a.timer"], deps)
        self.assertEqual(ordered, ["b.timer", "a.timer"])
        self.assertTrue(any("Dependency loop" in msg for msg in cm.output))


class SystemdUnitDependencyTests(unittest.TestCase):
    """
    Tests for the unit dependency interfaces using live systemd units.
    """

    def _write_unit_drop_in(self, unit_name, drop_in_name, content):
        """
        Write an arbitrary drop-in file for ``unit_name`` and reload the
        systemd manager configuration.
        """
        drop_in_dir = _DROP_IN_DIR_FMT % unit_name
        drop_in_file = os.path.join(drop_in_dir, drop_in_name)
        os.makedirs(drop_in_dir, exist_ok=True)
        with open(drop_in_file, "w", encoding="utf8") as f:
            f.write(content)
        run(["systemctl", "daemon-reload"], check=True)
        return (drop_in_dir, drop_in_file)

    def _remove_unit_drop_in(self, drop_in_dir, drop_in_file):
        """
        Remove a drop-in file written by ``_write_unit_drop_in()`` and reload
        the systemd manager configuration.
        """
        if os.path.exists(drop_in_file):
            os.unlink(drop_in_file)
        if os.path.exists(drop_in_dir):
            os.rmdir(drop_in_dir)
        run(["systemctl", "daemon-reload"], check=True)

    def test_unit_dependencies_nonexistent_unit(self):
        """
        Verify that a unit with no unit file has no dependencies.
        """
        self.assertEqual(
            _unit_dependencies("snapm-no-such-unit.service"), (set(), set())
        )

    def test_unit_dependencies_invalid_unit_name(self):
        """
        Verify that a unit that cannot be loaded has no dependencies.
        """
        self.assertEqual(_unit_dependencies("not a unit name"), (set(), set()))

    def test_unit_dependencies_target_unit(self):
        """
        Verify that the dependencies of a well known system target are
        reported in the expected direction.
        """
        (depends, depended) = _unit_dependencies("basic.target")
        self.assertIn("sysinit.target", depends)
        self.assertIn("multi-user.target", depended)

    def test_sort_units_system_targets(self):
        """
        Verify that live system targets are sorted into stop order: the
        later target is stopped before the target that it is ordered after.
        """
        targets = ["sysinit.target", "multi-user.target", "basic.target"]
        self.assertEqual(
            sort_units(targets),
            ["multi-user.target", "basic.target", "sysinit.target"],
        )

    def test_sort_units_timer_units_with_drop_in(self):
        """
        Verify that dependencies declared by a unit drop-in file order the
        snapm timer units.
        """
        create_unit = _UNIT_FORMATS[_UNIT_CREATE] % "sorttest"
        gc_unit = _UNIT_FORMATS[_UNIT_GC] % "sorttest"
        content = f"[Unit]\nRequires={gc_unit}\nAfter={gc_unit}\n"

        drop_in_dir = _DROP_IN_DIR_FMT % create_unit
        drop_in_file = os.path.join(drop_in_dir, "20-after.conf")
        try:
            self._write_unit_drop_in(create_unit, "20-after.conf", content)
            (depends, _) = _unit_dependencies(create_unit)
            self.assertIn(gc_unit, depends)

            # The create timer requires the gc timer: it must be stopped
            # first and started last.
            self.assertEqual(
                sort_units([gc_unit, create_unit]), [create_unit, gc_unit]
            )
            self.assertEqual(
                sort_units([create_unit, gc_unit]), [create_unit, gc_unit]
            )
        finally:
            self._remove_unit_drop_in(drop_in_dir, drop_in_file)
