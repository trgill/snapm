# Copyright Red Hat
#
# snapm/manager/calendar.py - Snapshot Manager CalendarSpec support
#
# This file is part of the snapm project.
#
# SPDX-License-Identifier: Apache-2.0
"""
Calendar event abstraction for Snapshot Manager
"""
from subprocess import run
from datetime import datetime, timedelta
import re

from snapm import SnapmCalloutError


_sd_analyze_calendar = ["systemd-analyze", "calendar"]

_ORIGINAL_FORM = "Original form"
_NORMALIZED_FORM = "Normalized form"
_NEXT_ELAPSE = "Next elapse"
_IN_UTC = "(in UTC)"
_FROM_NOW = "From now"
_NEVER = "never"

_TIME_FMT = "%a %Y-%m-%d %H:%M:%S %Z"

_TIME_REGEX = re.compile(r"\d{1,2}:\d{1,2}:\d{1,2}\.\d+")

USECS_PER_SEC = 1000000


class CalendarSpec:
    """
    Class representing systemd CalendarSpec expressions.
    """

    def _refresh(self):
        """
        Refresh this ``CalendarSpec`` object's time-dependent properties.
        """

        def strip_field(line):
            """
            Strip the field name from the string ``line``.
            """
            return line.split(": ", 1)[1].strip()

        def parse_usecs(time):
            """
            Parse the microseconds component of a time string and return it
            as a timedelta object.
            """
            parts = time.split()
            for part in parts:
                if _TIME_REGEX.match(part):
                    _, _, frac = part.partition(".")
                    frac, _, rep = frac.partition("/")
                    frac = int(frac.ljust(6, "0"))  # Convert to microseconds
                    rep = float(rep) if rep else 0.0
                    return timedelta(
                        microseconds=USECS_PER_SEC * (rep + frac / USECS_PER_SEC)
                    )

            return timedelta(0)

        sd_cmd_args = _sd_analyze_calendar + [self._calendarspec]
        sd_cmd = run(
            sd_cmd_args,
            encoding="utf8",
            capture_output=True,
            check=False,
        )

        if sd_cmd.returncode == 1:
            raise ValueError(f"Invalid CalendarSpec expression: {self._calendarspec}")
        if sd_cmd.returncode != 0:  # pragma: no cover
            raise SnapmCalloutError(
                f"Error calling systemd-analyze: {sd_cmd.stderr.decode('utf8')}"
            )

        carry_usecs = timedelta(0)
        for line in sd_cmd.stdout.splitlines():
            line = line.strip()
            if line.startswith(_ORIGINAL_FORM):
                continue
            if line.startswith(_NORMALIZED_FORM):
                self.normalized = strip_field(line)
                carry_usecs = parse_usecs(self.normalized)
            if line.startswith(_NEXT_ELAPSE):
                date_str = strip_field(line)
                if date_str == _NEVER:
                    self._next_elapse = None
                    self._in_utc = None
                    self._from_now = _NEVER
                    continue
                self._next_elapse = datetime.strptime(date_str, _TIME_FMT) + carry_usecs
                if date_str.endswith("UTC"):
                    self._in_utc = True
            if line.startswith(_IN_UTC):
                date_str = strip_field(line)
                self._in_utc = datetime.strptime(date_str, _TIME_FMT) + carry_usecs
            if line.startswith(_FROM_NOW):
                self._from_now = strip_field(line)

    def _cond_refresh(self):
        """
        Refresh this ``CalendarSpec`` object's time-dependent properties if the
        current ``next_elapse`` value is in the past.
        """
        # CalendarSpec instances that never occur do not need to be refreshed.
        if self._next_elapse is not None and self._next_elapse < datetime.now():
            self._refresh()

    def __init__(self, calendarspec: str):
        """
        Validate and parse a systemd calendarspec expression into a
        CalendarSpec object.

        :param calendarspec: A string containing an calendarspec expression.
        :raises: ``ValueError`` if ``calendarspec`` is not a valid calendarspec
                 expression.
        """
        self._calendarspec = calendarspec
        self._refresh()

    @property
    def next_elapse(self):
        """
        Return the next elapse time for this ``CalendarSpec`` object as an
        instance of ``datetime.datetime``.

        :returns: The next elapse time as a ``datetime`` object.
        :rtype: ``datetime.datetime``
        """
        self._cond_refresh()
        return self._next_elapse

    @property
    def in_utc(self):
        """
        Return the next elapse time for this ``CalendarSpec`` object as an
        instance of ``datetime.datetime`` in UTC.

        :returns: The next elapse time as a UTC ``datetime`` object.
        :rtype: ``datetime.datetime``
        """
        self._cond_refresh()
        self._cond_refresh()
        return self._in_utc

    @property
    def from_now(self):
        """
        Return a string representation of the time remaining until this
        ``CalendarSpec`` next elapses.

        :returns: The time remaining until the next elapse as a string.
        :rtype: str
        """
        self._cond_refresh()
        return self._from_now

    @property
    def occurs(self):
        """
        ``True`` if this ``CalendarSpec`` object's calendar expression will
        occur in the future, or ``False`` otherwise.
        """
        return (
            self.next_elapse is not None
            and self.in_utc is not None
            and self.from_now != _NEVER
        )

    @property
    def original(self):
        """
        The original form of this ``CalendarSpec`` as a string.
        """
        return self._calendarspec

    def __str__(self):
        """
        Return a string representation of this ``CalendarSpec`` instance.
        """
        return self._calendarspec

    def __repr__(self):
        """
        Return a string representation of this ``CalendarSpec`` instance in the
        form of a call to the CalendarSpec initializer.
        """
        return f'CalendarSpec("{str(self)}")'
