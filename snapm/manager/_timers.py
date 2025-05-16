# Copyright Red Hat
#
# snapm/manager/_systemd.py - Snapshot Manager systemd inteface
#
# This file is part of the snapm project.
#
# SPDX-License-Identifier: Apache-2.0
"""
Systemd timer integration for Snapshot Manager.
"""
import os
import time
import logging
import tempfile

import dbus

from snapm import SnapmArgumentError, SnapmTimerError, SnapmCalloutError

from ._calendar import CalendarSpec

_log = logging.getLogger(__name__)

_log_debug = _log.debug
_log_info = _log.info
_log_warn = _log.warning
_log_error = _log.error

# Constants for timer template units
UNIT_CREATE = "create"
UNIT_GC = "gc"

_VALID_UNITS = [
    UNIT_CREATE,
    UNIT_GC,
]

# Constants for timer operations
TIMER_ENABLE = "ENABLE"
TIMER_DISABLE = "DISABLE"
TIMER_START = "START"
TIMER_STOP = "STOP"

_VALID_OPS = [
    TIMER_ENABLE,
    TIMER_DISABLE,
    TIMER_START,
    TIMER_STOP,
]

# Format strings for snapm managed systemd units
_UNIT_FORMATS = {
    UNIT_CREATE: "snapm-create@%s.timer",
    UNIT_GC: "snapm-gc@%s.timer",
}

# Constants for systemd paths
_LIB_SYSTEMD_SYSTEM = "/lib/systemd/system"
_ETC_SYSTEMD_SYSTEM = "/etc/systemd/system"

# Constants for systemd DBus interface
_SYSTEMD_TOP_OBJECT = "org.freedesktop.systemd1"
_SYSTEMD_TOP_PATH = "/org/freedesktop/systemd1"
_ORG_FREEDESTOP_DBUS_PROPS = "org.freedesktop.DBus.Properties"

# Constants for timer unit drop-in file
_10_ON_CALENDAR_CONF = "10-oncalendar.conf"
_DROP_IN_FILE_MODE = 0o644


def _write_drop_in(drop_in_dir: str, drop_in_file: str, calendarspec: CalendarSpec):
    """
    Helper function for robustly writing unit drop-in files. Ensures that both
    the file data and metadata (including that of the containing directory)
    reach disk.

    :param drop_in_dir: The path to the systemd drop-in directory to use.
    :param drop_in_file: The name of the systemd drop-in configuration file.
    :param calendarspec: The CalendarSpec object representing the timer
                         configuration.
    """
    try:
        # Ensure the drop-in directory exists
        os.makedirs(drop_in_dir, exist_ok=True)

        # Write the drop-in configuration file atomically
        fd, tmp_path = tempfile.mkstemp(dir=drop_in_dir, prefix=".tmp_", text=True)
        try:
            with os.fdopen(fd, "w") as f:
                f.write(f"[Timer]\nOnCalendar={calendarspec.original}\n")
                f.flush()
                os.fdatasync(f.fileno())
            os.rename(tmp_path, drop_in_file)
            os.chmod(drop_in_file, _DROP_IN_FILE_MODE)

            # Ensure directory metadata is written to disk
            dir_fd = os.open(drop_in_dir, os.O_DIRECTORY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError as err:  # pragma: no cover
            os.unlink(tmp_path)
            raise SnapmTimerError(
                f"Filesystem error while writing drop-in file: {err}"
            ) from err
    except OSError as err:  # pragma: no cover
        raise SnapmTimerError(f"Filesystem error: {err}") from err


def _remove_drop_in(drop_in_dir: str, drop_in_file: str):
    """
    Helper function to remove a unit drop-in directory. The directory must
    contain exactly one file: ``drop_in_file`` which will be unlinked before
    calling ``os.rmdir()`` for the containing directory.

    :param drop_in_dir: The path to the systemd drop-in directory to use.
    :param drop_in_file: The name of the systemd drop-in configuration file.
    """
    try:
        os.unlink(drop_in_file)
        os.rmdir(drop_in_dir)
    except OSError as err:  # pragma: no cover
        _log_error(
            "Error cleaning up unit drop-in directory '%s': %s", drop_in_dir, err
        )
        raise SnapmTimerError(
            f"Failed to clean up drop-in file '{drop_in_file}': {err}"
        ) from err


def _enable_timer(unit_fmt: str, instance: str, calendarspec: CalendarSpec):
    """
    Enable an ``instance`` of the timer unit represented by ``unit_fmt``
    using the ``CalendarSpec`` object ``calendarspec`` to parameterize
    the timer.

    This must be called before attempting to start the timer unit.

    :param unit_fmt: A format string specifying the template unit.
    :param instance: A string naming the timer unit instance.
    :param calendarspec: A ``CalendarSpec`` object initialised with the
           desired OnCalendar expression.
    """
    unit_name = unit_fmt % instance
    drop_in_dir = f"{_ETC_SYSTEMD_SYSTEM}/{unit_name}.d"
    drop_in_file = os.path.join(drop_in_dir, _10_ON_CALENDAR_CONF)

    _write_drop_in(drop_in_dir, drop_in_file, calendarspec)

    try:
        # Connect to the systemd DBus interface
        bus = dbus.SystemBus()
        systemd = bus.get_object(
            _SYSTEMD_TOP_OBJECT,
            _SYSTEMD_TOP_PATH,
        )
        manager = dbus.Interface(systemd, f"{_SYSTEMD_TOP_OBJECT}.Manager")

        # Load the unit explicitly
        manager.LoadUnit(unit_name)

        # Enable the timer unit
        manager.EnableUnitFiles([unit_name], False, True)

        # Reload systemd to register the new unit
        manager.Reload()

    except dbus.DBusException as err:  # pragma: no cover
        raise SnapmTimerError(f"DBus error: {err}") from err


def _start_timer(unit_fmt: str, instance: str):
    """
    Start an ``instance`` of the timer unit represented by ``unit_fmt``
    after a previous call to ``enable_timer()``.

    :param unit_fmt: A format string specifying the template unit.
    :param instance: A string naming the timer unit instance.
    :param calendarspec: A ``CalendarSpec`` object initialised with the
           desired OnCalendar expression.
    """
    unit_name = unit_fmt % instance

    try:
        # Connect to the systemd DBus interface
        bus = dbus.SystemBus()
        systemd = bus.get_object(
            _SYSTEMD_TOP_OBJECT,
            _SYSTEMD_TOP_PATH,
        )
        manager = dbus.Interface(systemd, f"{_SYSTEMD_TOP_OBJECT}.Manager")

        # Start the timer unit
        manager.StartUnit(unit_name, "replace")

        # Poll for unit activation
        for _ in range(10):  # Try for ~1 seconds (10 * 0.1s)
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
            time.sleep(0.1)

        raise SnapmTimerError(f"Failed to activate {unit_name}.")  # pragma: no cover

    except dbus.DBusException as err:  # pragma: no cover
        raise SnapmTimerError(f"DBus error: {err}") from err


def _stop_timer(unit_fmt: str, instance: str):
    """
    Stop an ``instance`` of the timer unit represented by ``unit_fmt``
    previously started by calling ``_start_timer(unit_fmt, instance)``.

    :param instance: A string naming the timer unit instance.
    """
    unit_name = unit_fmt % instance

    try:
        # Connect to the systemd DBus interface
        bus = dbus.SystemBus()
        systemd = bus.get_object(
            _SYSTEMD_TOP_OBJECT,
            _SYSTEMD_TOP_PATH,
        )
        manager = dbus.Interface(systemd, f"{_SYSTEMD_TOP_OBJECT}.Manager")

        # Stop the timer unit
        manager.StopUnit(unit_name, "replace")

        _log_info("%s has been stopped.", unit_name)

    except dbus.DBusException as err:  # pragma: no cover
        _log_error("DBus error: %s", err)
        raise SnapmTimerError(f"DBus error: {err}") from err


def _disable_timer(unit_fmt: str, instance: str):
    """
    Disable an ``instance`` of the timer unit represented by ``unit_fmt``
    previously enabled by calling ``_enable_timer(unit_fmt, instance)``.

    :param instance: A string naming the timer unit instance.
    """
    unit_name = unit_fmt % instance
    drop_in_dir = f"{_ETC_SYSTEMD_SYSTEM}/{unit_name}.d"
    drop_in_file = os.path.join(drop_in_dir, _10_ON_CALENDAR_CONF)

    try:
        # Connect to the systemd DBus interface
        bus = dbus.SystemBus()
        systemd = bus.get_object(
            _SYSTEMD_TOP_OBJECT,
            _SYSTEMD_TOP_PATH,
        )
        manager = dbus.Interface(systemd, f"{_SYSTEMD_TOP_OBJECT}.Manager")

        # Stop and disable the timer unit
        manager.StopUnit(unit_name, "replace")
        manager.DisableUnitFiles([unit_name], False)

        # Reload systemd to register the new unit
        manager.Reload()

        _log_info("%s has been disabled and stopped.", unit_name)

    except dbus.DBusException as err:  # pragma: no cover
        _log_error("DBus error disabling timer: %s", err)
        raise SnapmTimerError(f"Failed to disable timer unit: {err}") from err

    _remove_drop_in(drop_in_dir, drop_in_file)


_OP_FNS = {
    # TIMER_ENABLE is special as it takes an additional calendarspec arg
    TIMER_ENABLE: _enable_timer,
    TIMER_DISABLE: _disable_timer,
    TIMER_START: _start_timer,
    TIMER_STOP: _stop_timer,
}


def timer(op: str, unit: str, instance: str, calendarspec=None):
    """
    Enable, disable, start, or stop a systemd timer unit.

    Create, modify, or remove an ``instance`` of timer unit ``unit`` according
    to the value of ``op``.

    Valid operations are:

        TIMER_ENABLE  - Create and enable a new timer
        TIMER_DISABLE - Disable and remove an existing timer
        TIMER_START   - Start an existing timer
        TIMER_STOP    - Stop an existing timer

    Valid units are:

        UNIT_CREATE  - An instance of the snapset create timer
        UNIT_GC      - An instance of the snapset gc timer

    The ``instance`` is a unique descriptive name for the timer that
    is used as the instance portion of the unit name when template
    units are instantiated, for example 'foo-timer@instance.timer'.

    When creating a timer the calendarspec argument should be either a
    string like value corresponding to a calendarspec expression, or an
    instance of ``snapm.manager._calendar.CalendarSpec``.

    :param op: The operation to perform.
    :param unit: The unit template to act on.
    :param instance: The instance string to instantiate.
    :param calendarspec: A calendarspec string or ``CalendarSpec``
                         instance describing the ``OnCalendar`` value
                         for a newly created timer instance.
    """
    if op not in _VALID_OPS:
        raise SnapmArgumentError(f"Invalid timer operation: {op}")
    if unit not in _VALID_UNITS:
        raise SnapmArgumentError(f"Invalid timer unit: {unit}")
    if not instance:
        raise SnapmArgumentError("Timer instance cannot be empty")
    if op != TIMER_ENABLE and calendarspec is not None:
        raise SnapmArgumentError(f"Timer {op} does not accept calendarspec=")

    fmt = _UNIT_FORMATS[unit]
    op_fn = _OP_FNS[op]

    if op == TIMER_ENABLE:
        if not calendarspec:
            raise SnapmArgumentError(f"Timer {op} requires non-empty calendarspec")
        if not isinstance(calendarspec, CalendarSpec):
            try:
                calendarspec = CalendarSpec(calendarspec)
            except ValueError as err:
                raise SnapmArgumentError(
                    "Timer {op}: invalid calendarspec string"
                ) from err
            except SnapmCalloutError as err:  # pragma: no cover
                raise SnapmTimerError("Error creating CalendarSpec") from err
        return op_fn(fmt, instance, calendarspec)
    return op_fn(fmt, instance)


__all__ = [
    "UNIT_CREATE",
    "UNIT_GC",
    "TIMER_ENABLE",
    "TIMER_DISABLE",
    "TIMER_START",
    "TIMER_STOP",
    "timer",
]
