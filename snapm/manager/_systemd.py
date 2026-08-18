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

from snapm import SnapmTimerError

_log = logging.getLogger(__name__)

_log_debug = _log.debug
_log_info = _log.info
_log_warn = _log.warning
_log_error = _log.error

# Constants for systemd DBus interface
_SYSTEMD_TOP_OBJECT = "org.freedesktop.systemd1"
_SYSTEMD_TOP_PATH = "/org/freedesktop/systemd1"
_ORG_FREEDESTOP_DBUS_PROPS = "org.freedesktop.DBus.Properties"


class UnitStatus(Enum):
    """
    Enum class representing the possible unit status values.
    """

    DISABLED = "disable"
    ENABLED = "enabled"
    RUNNING = "running"
    STOPPED = "stopped"
    INVALID = "invalid"


def _enable_unit(unit_name: str):
    """
    Enable a systemd unit.

    This must be called before attempting to start the unit.

    :param unit_name: A string specifying the unit name.
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
        raise SnapmTimerError(f"DBus error: {err}") from err


def _start_unit(unit_name: str):
    """
    Start a unit represented by ``unit_name`` after a previous call to
    ``_enable_unit()``.

    :param unit_name: A string specifying the unit name.
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

        raise SnapmTimerError(f"Failed to activate {unit_name}.")  # pragma: no cover

    except dbus.DBusException as err:  # pragma: no cover
        raise SnapmTimerError(f"DBus error: {err}") from err


def _stop_unit(unit_name: str):
    """
    Stop a unit represented by ``unit_name``.

    :param unit_name: A string naming the unit.
    """
    try:
        bus = dbus.SystemBus()
        systemd = bus.get_object(
            _SYSTEMD_TOP_OBJECT,
            _SYSTEMD_TOP_PATH,
        )
        manager = dbus.Interface(systemd, f"{_SYSTEMD_TOP_OBJECT}.Manager")

        manager.StopUnit(unit_name, "replace")

        _log_info("%s has been stopped.", unit_name)

    except dbus.DBusException as err:  # pragma: no cover
        _log_error("DBus error: %s", err)
        raise SnapmTimerError(f"DBus error: {err}") from err


def _disable_unit(unit_name: str):
    """
    Disable the unit represented by ``unit_name``.

    :param unit_name: A string naming the unit.
    """
    try:
        bus = dbus.SystemBus()
        systemd = bus.get_object(
            _SYSTEMD_TOP_OBJECT,
            _SYSTEMD_TOP_PATH,
        )
        manager = dbus.Interface(systemd, f"{_SYSTEMD_TOP_OBJECT}.Manager")

        _stop_unit(unit_name)
        manager.DisableUnitFiles([unit_name], False)
        manager.Reload()

        _log_info("%s has been disabled and stopped.", unit_name)

    except dbus.DBusException as err:  # pragma: no cover
        _log_error("DBus error disabling unit: %s", err)
        raise SnapmTimerError(f"Failed to disable unit: {err}") from err


def _unit_status(unit_name: str):
    """
    Obtain status of unit ``unit_name``. Returns an instance of ``UnitStatus``
    reflecting the current state of the unit.

    :param unit_name: A string naming the unit.
    :returns: The current status of the unit.
    :rtype: ``UnitStatus``
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
            return UnitStatus.DISABLED

        unit = bus.get_object(_SYSTEMD_TOP_OBJECT, str(unit_obj_path))
        unit_props = dbus.Interface(unit, _ORG_FREEDESTOP_DBUS_PROPS)

        load_state = unit_props.Get(f"{_SYSTEMD_TOP_OBJECT}.Unit", "LoadState")
        active_state = unit_props.Get(
            f"{_SYSTEMD_TOP_OBJECT}.Unit", "ActiveState"
        )

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
                return UnitStatus.ENABLED
        return UnitStatus.INVALID  # pragma: no cover

    except dbus.DBusException as err:  # pragma: no cover
        _log_error("DBus error getting status for unit: %s", err)
        raise SnapmTimerError(f"Failed to get unit status: {err}") from err


__all__ = [
    "UnitStatus",
    "_enable_unit",
    "_start_unit",
    "_stop_unit",
    "_disable_unit",
    "_unit_status",
]
