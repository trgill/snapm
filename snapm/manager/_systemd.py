# Copyright Red Hat
#
# snapm/manager/_systemd.py - Snapshot Manager systemd interface
#
# This file is part of the snapm project.
#
# SPDX-License-Identifier: Apache-2.0
"""
General systemd unit management for Snapshot Manager.
"""
import time
import logging
from enum import Enum

import dbus

from snapm import SnapmSystemdError

_log = logging.getLogger(__name__)

_log_debug = _log.debug
_log_info = _log.info
_log_warn = _log.warning
_log_error = _log.error

# Constants for systemd DBus interface
_SYSTEMD_TOP_OBJECT = "org.freedesktop.systemd1"
_SYSTEMD_TOP_PATH = "/org/freedesktop/systemd1"
_ORG_FREEDESTOP_DBUS_PROPS = "org.freedesktop.DBus.Properties"

# Unit properties naming units that this unit is ordered after.
_UNIT_DEPENDS_PROPERTIES = ("After",)

# Unit properties naming units that this unit is ordered before.
_UNIT_DEPENDED_PROPERTIES = ("Before",)


class UnitStatus(Enum):
    """
    Enum class representing the possible unit status values.
    """

    DISABLED = "disable"
    ENABLED = "enabled"
    RUNNING = "running"
    STOPPED = "stopped"
    INVALID = "invalid"


def enable_unit(unit_name: str):
    """
    Enable a systemd unit.

    This must be called before attempting to start the unit.

    :param unit_name: A string specifying the unit name.
    :raises: ``SnapmSystemdError`` if the unit could not be enabled.
    """
    try:
        bus = dbus.SystemBus()
        systemd = bus.get_object(
            _SYSTEMD_TOP_OBJECT,
            _SYSTEMD_TOP_PATH,
        )
        manager = dbus.Interface(systemd, f"{_SYSTEMD_TOP_OBJECT}.Manager")

        manager.LoadUnit(unit_name)
        manager.EnableUnitFiles([unit_name], False, True)
        manager.Reload()

    except dbus.DBusException as err:  # pragma: no cover
        raise SnapmSystemdError(f"DBus error: {err}") from err


def start_unit(unit_name: str):
    """
    Start a unit represented by ``unit_name`` after a previous call to
    ``enable_unit()``.

    :param unit_name: A string specifying the unit name.
    :raises: ``SnapmSystemdError`` if the unit could not be started.
    """
    try:
        bus = dbus.SystemBus()
        systemd = bus.get_object(
            _SYSTEMD_TOP_OBJECT,
            _SYSTEMD_TOP_PATH,
        )
        manager = dbus.Interface(systemd, f"{_SYSTEMD_TOP_OBJECT}.Manager")

        manager.StartUnit(unit_name, "replace")

        for _ in range(10):
            try:
                unit_obj_path = manager.GetUnit(unit_name)
                unit = bus.get_object(_SYSTEMD_TOP_OBJECT, str(unit_obj_path))
                unit_props = dbus.Interface(unit, _ORG_FREEDESTOP_DBUS_PROPS)
                active_state = unit_props.Get(
                    f"{_SYSTEMD_TOP_OBJECT}.Unit", "ActiveState"
                )
                if active_state == "active":
                    _log_info("%s is active.", unit_name)
                    return
            except dbus.DBusException:  # pragma: no cover
                pass
            time.sleep(0.1)  # pragma: no cover

        raise SnapmSystemdError(f"Failed to activate {unit_name}.")  # pragma: no cover

    except dbus.DBusException as err:  # pragma: no cover
        raise SnapmSystemdError(f"DBus error: {err}") from err


def stop_unit(unit_name: str):
    """
    Stop a unit represented by ``unit_name``.

    :param unit_name: A string naming the unit.
    :raises: ``SnapmSystemdError`` if the unit could not be stopped.
    """
    try:
        bus = dbus.SystemBus()
        systemd = bus.get_object(
            _SYSTEMD_TOP_OBJECT,
            _SYSTEMD_TOP_PATH,
        )
        manager = dbus.Interface(systemd, f"{_SYSTEMD_TOP_OBJECT}.Manager")

        manager.StopUnit(unit_name, "replace")

        for _ in range(10):
            try:
                unit_obj_path = manager.GetUnit(unit_name)
                unit = bus.get_object(_SYSTEMD_TOP_OBJECT, str(unit_obj_path))
                unit_props = dbus.Interface(unit, _ORG_FREEDESTOP_DBUS_PROPS)
                active_state = unit_props.Get(
                    f"{_SYSTEMD_TOP_OBJECT}.Unit", "ActiveState"
                )
                if active_state == "inactive":
                    _log_info("%s has been stopped.", unit_name)
                    return
            except dbus.DBusException as err:  # pragma: no cover
                if err.get_dbus_name() == "org.freedesktop.systemd1.NoSuchUnit":
                    _log_info("%s has been stopped.", unit_name)
                    return
                raise
            time.sleep(0.1)  # pragma: no cover

        raise SnapmSystemdError(  # pragma: no cover
            f"Failed to deactivate {unit_name}."
        )

    except dbus.DBusException as err:  # pragma: no cover
        _log_error("DBus error: %s", err)
        raise SnapmSystemdError(f"DBus error: {err}") from err


def disable_unit(unit_name: str):
    """
    Disable the unit represented by ``unit_name``.

    :param unit_name: A string naming the unit.
    :raises: ``SnapmSystemdError`` if the unit could not be disabled.
    """
    try:
        bus = dbus.SystemBus()
        systemd = bus.get_object(
            _SYSTEMD_TOP_OBJECT,
            _SYSTEMD_TOP_PATH,
        )
        manager = dbus.Interface(systemd, f"{_SYSTEMD_TOP_OBJECT}.Manager")

        stop_unit(unit_name)
        manager.DisableUnitFiles([unit_name], False)
        manager.Reload()

        _log_info("%s has been disabled and stopped.", unit_name)

    except dbus.DBusException as err:  # pragma: no cover
        _log_error("DBus error disabling unit: %s", err)
        raise SnapmSystemdError(f"Failed to disable unit: {err}") from err


def unit_status(unit_name: str):
    """
    Obtain status of unit ``unit_name``. Returns an instance of ``UnitStatus``
    reflecting the current state of the unit.

    :param unit_name: A string naming the unit.
    :returns: The current status of the unit.
    :rtype: ``UnitStatus``
    :raises: ``SnapmSystemdError`` if the unit status could not be obtained.
    """
    try:
        bus = dbus.SystemBus()
        systemd = bus.get_object(
            _SYSTEMD_TOP_OBJECT,
            _SYSTEMD_TOP_PATH,
        )
        manager = dbus.Interface(systemd, f"{_SYSTEMD_TOP_OBJECT}.Manager")

        try:
            unit_obj_path = manager.GetUnit(unit_name)
        except dbus.DBusException as err:  # pragma: no cover
            if err.get_dbus_name() != "org.freedesktop.systemd1.NoSuchUnit":
                raise err
            try:
                unit_file_state = manager.GetUnitFileState(unit_name)
                if unit_file_state == "enabled":
                    return UnitStatus.ENABLED
            except dbus.DBusException as err2:
                if err2.get_dbus_name() not in (
                    "org.freedesktop.DBus.Error.FileNotFound",
                    "org.freedesktop.systemd1.NoSuchUnit",
                ):
                    raise
            return UnitStatus.DISABLED

        unit = bus.get_object(_SYSTEMD_TOP_OBJECT, str(unit_obj_path))
        unit_props = dbus.Interface(unit, _ORG_FREEDESTOP_DBUS_PROPS)

        load_state = unit_props.Get(f"{_SYSTEMD_TOP_OBJECT}.Unit", "LoadState")
        active_state = unit_props.Get(f"{_SYSTEMD_TOP_OBJECT}.Unit", "ActiveState")

        _log_debug(
            "unit(%s) state load: %s, active: %s",
            unit_name,
            load_state,
            active_state,
        )

        if load_state == "loaded":
            if active_state == "active":
                return UnitStatus.RUNNING
            if active_state == "inactive":
                unit_file_state = unit_props.Get(
                    f"{_SYSTEMD_TOP_OBJECT}.Unit", "UnitFileState"
                )
                if unit_file_state == "enabled":
                    return UnitStatus.ENABLED
                return UnitStatus.DISABLED
        return UnitStatus.INVALID  # pragma: no cover

    except dbus.DBusException as err:  # pragma: no cover
        _log_error("DBus error getting status for unit: %s", err)
        raise SnapmSystemdError(f"Failed to get unit status: {err}") from err


def _unit_dependencies(unit_name: str):
    """
    Obtain the dependencies of the unit ``unit_name``.

    Two sets of unit names are returned: units ordered before ``unit_name``
    by ``After``, and units ordered after it by ``Before``.

    A unit that cannot be loaded, for example because no corresponding unit
    file exists, has no dependencies: a pair of empty sets is returned in this
    case.

    :param unit_name: A string naming the unit.
    :returns: A tuple of two sets of unit names, ``(depends, depended)``.
    :rtype: tuple
    :raises: ``SnapmSystemdError`` if the unit dependencies could not be
             obtained.
    """
    try:
        bus = dbus.SystemBus()
        systemd = bus.get_object(
            _SYSTEMD_TOP_OBJECT,
            _SYSTEMD_TOP_PATH,
        )
        manager = dbus.Interface(systemd, f"{_SYSTEMD_TOP_OBJECT}.Manager")

        try:
            unit_obj_path = manager.LoadUnit(unit_name)
        except dbus.DBusException as err:
            _log_debug("Could not load unit %s: %s", unit_name, err)
            if err.get_dbus_name() not in (
                "org.freedesktop.systemd1.NoSuchUnit",
                "org.freedesktop.DBus.Error.InvalidArgs",
            ):
                raise
            return (set(), set())

        unit = bus.get_object(_SYSTEMD_TOP_OBJECT, str(unit_obj_path))
        unit_props = dbus.Interface(unit, _ORG_FREEDESTOP_DBUS_PROPS)
        props = unit_props.GetAll(f"{_SYSTEMD_TOP_OBJECT}.Unit")

        depends = set()
        for prop in _UNIT_DEPENDS_PROPERTIES:
            depends.update(str(name) for name in props.get(prop, []))

        depended = set()
        for prop in _UNIT_DEPENDED_PROPERTIES:
            depended.update(str(name) for name in props.get(prop, []))

        _log_debug(
            "unit(%s) depends on: %s, depended on by: %s",
            unit_name,
            ",".join(sorted(depends)) or "-",
            ",".join(sorted(depended)) or "-",
        )

        return (depends, depended)

    except dbus.DBusException as err:  # pragma: no cover
        _log_error("DBus error getting dependencies for unit: %s", err)
        raise SnapmSystemdError(f"Failed to get unit dependencies: {err}") from err


def sort_units(unit_names: list):
    """
    Sort the units named by ``unit_names`` into systemd dependency order.

    The returned list is ordered so that each unit precedes the units that it
    depends upon: a caller may stop the units by iterating over the list in
    order, stopping each unit in turn, and may reverse the operation by
    walking the list backwards, starting each unit in turn.

    Only dependencies between members of ``unit_names`` are considered:
    dependencies on units that are not named in the list are ignored.
    Duplicate names are removed and units with no dependency relationship
    retain their relative order from ``unit_names``.

    A dependency loop cannot be ordered: the loop is broken at the first
    remaining unit in list order and a warning is logged.

    :param unit_names: A list of strings naming the units to sort.
    :returns: A new list naming the units in dependency order.
    :rtype: list
    :raises: ``SnapmSystemdError`` if the unit dependencies could not be
             obtained.
    """
    # Remove duplicate names while preserving the caller's ordering
    units = list(dict.fromkeys(unit_names))
    if len(units) < 2:
        return units

    unit_set = set(units)

    # Map each unit to the set of units that must be stopped after it
    precedes = {unit: set() for unit in units}
    for unit in units:
        (depends, depended) = _unit_dependencies(unit)
        # This unit must be stopped before the units that it depends upon
        precedes[unit].update(depends & unit_set)
        # Units that depend upon this unit must be stopped before it
        for other in depended & unit_set:
            precedes[other].add(unit)
        precedes[unit].discard(unit)

    in_degree = {unit: 0 for unit in units}
    for others in precedes.values():
        for other in others:
            in_degree[other] += 1

    ordered = []
    remaining = list(units)
    while remaining:
        ready = next((unit for unit in remaining if not in_degree[unit]), None)
        if ready is None:
            ready = remaining[0]
            _log_warn(
                "Dependency loop sorting units: breaking loop at unit '%s'", ready
            )
        remaining.remove(ready)
        ordered.append(ready)
        for other in precedes[ready]:
            in_degree[other] -= 1

    _log_debug("Sorted units into dependency order: %s", ",".join(ordered))

    return ordered


__all__ = [
    "UnitStatus",
    "enable_unit",
    "start_unit",
    "stop_unit",
    "disable_unit",
    "unit_status",
    "sort_units",
]
