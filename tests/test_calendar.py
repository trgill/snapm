# Copyright Red Hat
#
# tests/test_calendar.py - CalendarSpec unit tests
#
# This file is part of the snapm project.
#
# SPDX-License-Identifier: Apache-2.0
from shutil import which
import unittest
import logging
import time
import os

import snapm.manager._calendar
from snapm.manager._calendar import CalendarSpec

log = logging.getLogger()

USECS_PER_SEC = 1000000
USECS_INFINITY = -1
TZ = "TZ"

_sd_analyze_orig = snapm.manager._calendar._sd_analyze_calendar


def have_faketime():
    """
    Return `True` if the `faketime` command is available, or `False`
    otherwise.
    """
    return which("faketime") is not None


def patch_sd_analyze(faketime):
    """
    Monkey-patch the calendar._sd_analyze_calendar list to inject
    ``faketime @faketime`` into the systemd-analyze command list.
    """
    faketime = float(faketime) / USECS_PER_SEC
    snapm.manager._calendar._sd_analyze_calendar = [
        "faketime",
        f"@{str(faketime)}",
        "systemd-analyze",
        "calendar",
    ]


def unpatch_sd_analyze():
    """
    Revert calendar._sd_analyze_calendar list faketime injection.
    """
    snapm.manager._calendar._sd_analyze_calendar = _sd_analyze_orig


class CalendarSpecTests(unittest.TestCase):
    """Test calendar module"""

    def _test_one(self, calin, calout):
        cs = CalendarSpec(calin)
        self.assertTrue(cs)
        self.assertTrue(cs.normalized == calout)

        if cs.occurs:
            self.assertTrue(cs.next_elapse is not None)

        cs2 = CalendarSpec(str(cs))

        self.assertEqual(str(cs), str(cs2))

        return True

    def _test_next(self, calin, new_tz, after, expect):
        old_tz = os.environ[TZ] if TZ in os.environ else ""

        if new_tz:
            new_tz = ":" + new_tz

        os.environ[TZ] = new_tz
        time.tzset()

        patch_sd_analyze(after)
        cs = CalendarSpec(calin)
        if cs.next_elapse:
            next_elapse_us = int(cs.next_elapse.timestamp()) * USECS_PER_SEC
            next_elapse_us += cs.next_elapse.microsecond
            self.assertEqual(next_elapse_us, expect)
        else:
            self.assertEqual(USECS_INFINITY, expect)

        unpatch_sd_analyze()
        os.environ[TZ] = old_tz
        time.tzset()

        return True

    def test_calendar_spec__repr__(self):
        cs = CalendarSpec("hourly")
        self.assertEqual(repr(cs), 'CalendarSpec("hourly")')

    def test_calendar_spec_invalid(self):
        with self.assertRaises(ValueError) as cm:
            cs = CalendarSpec("Mon Tue Two 2")

    def test_calendar_spec_one(self):
        data = [
            ("Sat,Thu,Mon-Wed,Sat-Sun", "Mon..Thu,Sat,Sun *-*-* 00:00:00"),
            ("Sat,Thu,Mon..Wed,Sat..Sun", "Mon..Thu,Sat,Sun *-*-* 00:00:00"),
            ("Mon,Sun 12-*-* 2,1:23", "Mon,Sun 2012-*-* 01,02:23:00"),
            ("Wed *-1", "Wed *-*-01 00:00:00"),
            ("Wed-Wed,Wed *-1", "Wed *-*-01 00:00:00"),
            ("Wed..Wed,Wed *-1", "Wed *-*-01 00:00:00"),
            ("Wed, 17:48", "Wed *-*-* 17:48:00"),
            ("Wednesday,", "Wed *-*-* 00:00:00"),
            ("Wed-Sat,Tue 12-10-15 1:2:3", "Tue..Sat 2012-10-15 01:02:03"),
            ("Wed..Sat,Tue 12-10-15 1:2:3", "Tue..Sat 2012-10-15 01:02:03"),
            ("*-*-7 0:0:0", "*-*-07 00:00:00"),
            ("10-15", "*-10-15 00:00:00"),
            ("monday *-12-* 17:00", "Mon *-12-* 17:00:00"),
            ("Mon,Fri *-*-3,1,2 *:30:45", "Mon,Fri *-*-01,02,03 *:30:45"),
            ("12,14,13,12:20,10,30", "*-*-* 12,13,14:10,20,30:00"),
            ("mon,fri *-1/2-1,3 *:30:45", "Mon,Fri *-01/2-01,03 *:30:45"),
            ("03-05 08:05:40", "*-03-05 08:05:40"),
            ("08:05:40", "*-*-* 08:05:40"),
            ("05:40", "*-*-* 05:40:00"),
            ("Sat,Sun 12-05 08:05:40", "Sat,Sun *-12-05 08:05:40"),
            ("Sat,Sun 08:05:40", "Sat,Sun *-*-* 08:05:40"),
            ("2003-03-05 05:40", "2003-03-05 05:40:00"),
            ("2003-03-05", "2003-03-05 00:00:00"),
            ("03-05", "*-03-05 00:00:00"),
            ("hourly", "*-*-* *:00:00"),
            ("daily", "*-*-* 00:00:00"),
            ("monthly", "*-*-01 00:00:00"),
            ("weekly", "Mon *-*-* 00:00:00"),
            ("minutely", "*-*-* *:*:00"),
            ("quarterly", "*-01,04,07,10-01 00:00:00"),
            ("semi-annually", "*-01,07-01 00:00:00"),
            ("annually", "*-01-01 00:00:00"),
            ("*:2/3", "*-*-* *:02/3:00"),
            ("2015-10-25 01:00:00 uTc", "2015-10-25 01:00:00 UTC"),
            ("2015-10-25 01:00:00 Asia/Vladivostok", "2015-10-25 01:00:00 Asia/Vladivostok"),
            ("weekly Pacific/Auckland", "Mon *-*-* 00:00:00 Pacific/Auckland"),
            ("2016-03-27 03:17:00.4200005", "2016-03-27 03:17:00.420001"),
            ("2016-03-27 03:17:00/0.42", "2016-03-27 03:17:00/0.420000"),
            # Ranges are not currently implemented
            #("9..11,13:00,30", "*-*-* 09..11,13:00,30:00"),
            #("1..3-1..3 1..3:1..3", "*-01..03-01..03 01..03:01..03:00"),
            #("00:00:1.125..2.125", "*-*-* 00:00:01.125000..02.125000"),
            #("00:00:1.0..3.8", "*-*-* 00:00:01..03"),
            #("00:00:01..03", "*-*-* 00:00:01..03"),
            #("00:00:01/2,02..03", "*-*-* 00:00:01/2,02..03"),
            ("*:4,30:0..3", "*-*-* *:04,30:00..03"),
            ("*:4,30:0/1", "*-*-* *:04,30:*"),
            ("*:4,30:0/1,3,5", "*-*-* *:04,30:*"),
            ("*-*~1 Utc", "*-*~01 00:00:00 UTC"),
            ("*-*~05,3 ", "*-*~03,05 00:00:00"),
            ("*-*~* 00:00:00", "*-*-* 00:00:00"),
            ("Monday", "Mon *-*-* 00:00:00"),
            ("Monday *-*-*", "Mon *-*-* 00:00:00"),
            ("*-*-*", "*-*-* 00:00:00"),
            ("*:*:*", "*-*-* *:*:*"),
            ("*:*", "*-*-* *:*:00"),
            ("12:*", "*-*-* 12:*:00"),
            ("*:30", "*-*-* *:30:00"),
            ("93..00-*-*", "1993..2000-*-* 00:00:00"),
            ("00..07-*-*", "2000..2007-*-* 00:00:00"),
            ("*:20..39/5", "*-*-* *:20..35/5:00"),
            ("00:00:20..40/1", "*-*-* 00:00:20..40"),
            ("*~03/1,03..05", "*-*~03/1,03..05 00:00:00"),
            # UNIX timestamps are always UTC
            ("@1493187147", "2017-04-26 06:12:27 UTC"),
            ("@1493187147 UTC", "2017-04-26 06:12:27 UTC"),
            ("@0", "1970-01-01 00:00:00 UTC"),
            ("@0 UTC", "1970-01-01 00:00:00 UTC"),
            ("*:05..05", "*-*-* *:05:00"),
            ("*:05..10/6", "*-*-* *:05:00"),
        ]
        for calin, calout in data:
            with self.subTest(f"Validating '{calin}' == '{calout}'", i=data.index((calin, calout))):
                self.assertTrue(self._test_one(calin, calout))

    @unittest.skipIf(not have_faketime(), "missing faketime command")
    def test_calendar_spec_next(self):
        data = [
            ("2016-03-27 03:17:00", "", 12345, 1459048620000000),
            ("2016-03-27 03:17:00", "Europe/Berlin", 12345, 1459041420000000),
            ("2016-03-27 03:17:00", "Europe/Kyiv", 12345, -1),
            ("2016-03-27 03:17:00 UTC", "", 12345, 1459048620000000),
            ("2016-03-27 03:17:00 UTC", "", 12345, 1459048620000000),
            ("2016-03-27 03:17:00 UTC", "Europe/Berlin", 12345, 1459048620000000),
            ("2016-03-27 03:17:00 UTC", "Europe/Kyiv", 12345, 1459048620000000),
            ("2016-03-27 03:17:00.420000001 UTC", "Europe/Kyiv", 12345, 1459048620420000),
            ("2016-03-27 03:17:00.4200005 UTC", "Europe/Kyiv", 12345, 1459048620420001),
            ("2015-11-13 09:11:23.42", "Europe/Kyiv", 12345, 1447398683420000),
            # systemd-analyze calendar only reports next elapsed with second precision:
            # expressions with fractional seconds repetition will be rounded down to the
            # nearest whole second.
            #("2015-11-13 09:11:23.42/1.77", "Europe/Kyiv", 1447398683420000, 1447398685190000),
            #("2015-11-13 09:11:23.42/1.77", "Europe/Kyiv", 1447398683419999, 1447398683420000),
            ("Sun 16:00:00", "Europe/Berlin", 1456041600123456, 1456066800000000),
            ("*-04-31", "", 12345, -1),
            ("2016-02~01 UTC", "", 12345, 1456704000000000),
            ("Mon 2017-05~01..07 UTC", "", 12345, 1496016000000000),
            ("Mon 2017-05~07/1 UTC", "", 12345, 1496016000000000),
            ("*-*-01/5 04:00:00 UTC", "", 1646010000000000, 1646107200000000),
            ("*-01/7-01 04:00:00 UTC", "", 1664607600000000, 1672545600000000),
            ("2017-08-06 9,11,13,15,17:00 UTC", "", 1502029800000000, 1502031600000000),
            ("2017-08-06 9..17/2:00 UTC", "", 1502029800000000, 1502031600000000),
            ("2016-12-* 3..21/6:00 UTC", "", 1482613200000001, 1482634800000000),
            ("2017-09-24 03:30:00 Pacific/Auckland", "", 12345, 1506177000000000),
            # Due to daylight saving time - 2017-09-24 02:30:00 does not exist
            ("2017-09-24 02:30:00 Pacific/Auckland", "", 12345, -1),
            ("2017-04-02 02:30:00 Pacific/Auckland", "", 12345, 1491053400000000),
            # Confirm that even though it's a time change here (backward), 02:30 happens only once
            ("2017-04-02 02:30:00 Pacific/Auckland", "", 1491053400000000, -1),
            ("2017-04-02 03:30:00 Pacific/Auckland", "", 12345, 1491060600000000),
            # Confirm that timezones in the Spec work regardless of current timezone
            ("2017-09-09 20:42:00 Pacific/Auckland", "", 12345, 1504946520000000),
            ("2017-09-09 20:42:00 Pacific/Auckland", "Europe/Kyiv", 12345, 1504946520000000),
            # Check that we don't start looping if mktime(), moves us backwards
            ("Sun *-*-* 01:00:00 Europe/Dublin", "", 1616412478000000, 1617494400000000),
            ("Sun *-*-* 01:00:00 Europe/Dublin", "IST", 1616412478000000, 1617494400000000),
        ]
        for calin, new_tz, after, expect in data:
            i = data.index((calin, new_tz, after, expect))
            with self.subTest(f"Validating '{calin}' next_elapse", i=i):
                self.assertTrue(self._test_next(calin, new_tz, after, expect))
