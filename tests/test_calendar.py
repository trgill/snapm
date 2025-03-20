# Copyright Red Hat
#
# tests/test_calendar.py - CalendarSpec unit tests
#
# This file is part of the snapm project.
#
# SPDX-License-Identifier: GPL-2.0-only
import unittest
import logging
import time
import os

import snapm.manager.calendar
from snapm.manager.calendar import CalendarSpec

log = logging.getLogger()

USECS_PER_SEC = 1000000
USECS_INFINITY = -1
TZ = "TZ"

_sd_analyze_orig = snapm.manager.calendar._sd_analyze_calendar


def patch_sd_analyze(faketime):
    """
    Monkey-patch the calendar._sd_analyze_calendar list to inject
    ``faketime @faketime`` into the systemd-analyze command list.
    """
    faketime = float(faketime) / USECS_PER_SEC
    snapm.manager.calendar._sd_analyze_calendar = [
        "faketime",
        f"@{str(faketime)}",
        "systemd-analyze",
        "calendar",
    ]


def unpatch_sd_analyze():
    """
    Revert calendar._sd_analyze_calendar list faketime injection.
    """
    snapm.manager.calendar._sd_analyze_calendar = _sd_analyze_orig


class CalendarSpecTests(unittest.TestCase):
    """Test calendar module"""

    def _test_one(self, calin, calout):
        cs = CalendarSpec(calin)
        self.assertTrue(cs)
        self.assertTrue(str(cs) == calout)

        if cs.occurs:
            self.assertTrue(cs.next_elapse is not None)

        cs2 = CalendarSpec(str(cs))

        self.assertEqual(str(cs), str(cs2))

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

    def test_calendar_spec_one(self):
        self._test_one("Sat,Thu,Mon-Wed,Sat-Sun", "Mon..Thu,Sat,Sun *-*-* 00:00:00")
        self._test_one("Sat,Thu,Mon..Wed,Sat..Sun", "Mon..Thu,Sat,Sun *-*-* 00:00:00")
        self._test_one("Mon,Sun 12-*-* 2,1:23", "Mon,Sun 2012-*-* 01,02:23:00")
        self._test_one("Wed *-1", "Wed *-*-01 00:00:00")
        self._test_one("Wed-Wed,Wed *-1", "Wed *-*-01 00:00:00")
        self._test_one("Wed..Wed,Wed *-1", "Wed *-*-01 00:00:00")
        self._test_one("Wed, 17:48", "Wed *-*-* 17:48:00")
        self._test_one("Wednesday,", "Wed *-*-* 00:00:00")
        self._test_one("Wed-Sat,Tue 12-10-15 1:2:3", "Tue..Sat 2012-10-15 01:02:03")
        self._test_one("Wed..Sat,Tue 12-10-15 1:2:3", "Tue..Sat 2012-10-15 01:02:03")
        self._test_one("*-*-7 0:0:0", "*-*-07 00:00:00")
        self._test_one("10-15", "*-10-15 00:00:00")
        self._test_one("monday *-12-* 17:00", "Mon *-12-* 17:00:00")
        self._test_one("Mon,Fri *-*-3,1,2 *:30:45", "Mon,Fri *-*-01,02,03 *:30:45")
        self._test_one("12,14,13,12:20,10,30", "*-*-* 12,13,14:10,20,30:00")
        self._test_one("mon,fri *-1/2-1,3 *:30:45", "Mon,Fri *-01/2-01,03 *:30:45")
        self._test_one("03-05 08:05:40", "*-03-05 08:05:40")
        self._test_one("08:05:40", "*-*-* 08:05:40")
        self._test_one("05:40", "*-*-* 05:40:00")
        self._test_one("Sat,Sun 12-05 08:05:40", "Sat,Sun *-12-05 08:05:40")
        self._test_one("Sat,Sun 08:05:40", "Sat,Sun *-*-* 08:05:40")
        self._test_one("2003-03-05 05:40", "2003-03-05 05:40:00")
        self._test_one("2003-03-05", "2003-03-05 00:00:00")
        self._test_one("03-05", "*-03-05 00:00:00")
        self._test_one("hourly", "*-*-* *:00:00")
        self._test_one("daily", "*-*-* 00:00:00")
        self._test_one("monthly", "*-*-01 00:00:00")
        self._test_one("weekly", "Mon *-*-* 00:00:00")
        self._test_one("minutely", "*-*-* *:*:00")
        self._test_one("quarterly", "*-01,04,07,10-01 00:00:00")
        self._test_one("semi-annually", "*-01,07-01 00:00:00")
        self._test_one("annually", "*-01-01 00:00:00")
        self._test_one("*:2/3", "*-*-* *:02/3:00")
        self._test_one("2015-10-25 01:00:00 uTc", "2015-10-25 01:00:00 UTC")
        self._test_one("2015-10-25 01:00:00 Asia/Vladivostok", "2015-10-25 01:00:00 Asia/Vladivostok")
        self._test_one("weekly Pacific/Auckland", "Mon *-*-* 00:00:00 Pacific/Auckland")
        self._test_one("2016-03-27 03:17:00.4200005", "2016-03-27 03:17:00.420001")
        self._test_one("2016-03-27 03:17:00/0.42", "2016-03-27 03:17:00/0.420000")
        # Ranges are not currently implemented
        #self._test_one("9..11,13:00,30", "*-*-* 09..11,13:00,30:00")
        #self._test_one("1..3-1..3 1..3:1..3", "*-01..03-01..03 01..03:01..03:00")
        #self._test_one("00:00:1.125..2.125", "*-*-* 00:00:01.125000..02.125000")
        #self._test_one("00:00:1.0..3.8", "*-*-* 00:00:01..03")
        #self._test_one("00:00:01..03", "*-*-* 00:00:01..03")
        #self._test_one("00:00:01/2,02..03", "*-*-* 00:00:01/2,02..03")
        self._test_one("*:4,30:0..3", "*-*-* *:04,30:00..03")
        self._test_one("*:4,30:0/1", "*-*-* *:04,30:*")
        self._test_one("*:4,30:0/1,3,5", "*-*-* *:04,30:*")
        self._test_one("*-*~1 Utc", "*-*~01 00:00:00 UTC")
        self._test_one("*-*~05,3 ", "*-*~03,05 00:00:00")
        self._test_one("*-*~* 00:00:00", "*-*-* 00:00:00")
        self._test_one("Monday", "Mon *-*-* 00:00:00")
        self._test_one("Monday *-*-*", "Mon *-*-* 00:00:00")
        self._test_one("*-*-*", "*-*-* 00:00:00")
        self._test_one("*:*:*", "*-*-* *:*:*")
        self._test_one("*:*", "*-*-* *:*:00")
        self._test_one("12:*", "*-*-* 12:*:00")
        self._test_one("*:30", "*-*-* *:30:00")
        self._test_one("93..00-*-*", "1993..2000-*-* 00:00:00")
        self._test_one("00..07-*-*", "2000..2007-*-* 00:00:00")
        self._test_one("*:20..39/5", "*-*-* *:20..35/5:00")
        self._test_one("00:00:20..40/1", "*-*-* 00:00:20..40")
        self._test_one("*~03/1,03..05", "*-*~03/1,03..05 00:00:00")
        # UNIX timestamps are always UTC
        self._test_one("@1493187147", "2017-04-26 06:12:27 UTC")
        self._test_one("@1493187147 UTC", "2017-04-26 06:12:27 UTC")
        self._test_one("@0", "1970-01-01 00:00:00 UTC")
        self._test_one("@0 UTC", "1970-01-01 00:00:00 UTC")
        self._test_one("*:05..05", "*-*-* *:05:00")
        self._test_one("*:05..10/6", "*-*-* *:05:00")

    def test_calendar_spec_next(self):
        self._test_next("2016-03-27 03:17:00", "", 12345, 1459048620000000)
        self._test_next("2016-03-27 03:17:00", "Europe/Berlin", 12345, 1459041420000000)
        self._test_next("2016-03-27 03:17:00", "Europe/Kyiv", 12345, -1)
        self._test_next("2016-03-27 03:17:00 UTC", "", 12345, 1459048620000000)
        self._test_next("2016-03-27 03:17:00 UTC", "", 12345, 1459048620000000)
        self._test_next("2016-03-27 03:17:00 UTC", "Europe/Berlin", 12345, 1459048620000000)
        self._test_next("2016-03-27 03:17:00 UTC", "Europe/Kyiv", 12345, 1459048620000000)
        self._test_next("2016-03-27 03:17:00.420000001 UTC", "Europe/Kyiv", 12345, 1459048620420000)
        self._test_next("2016-03-27 03:17:00.4200005 UTC", "Europe/Kyiv", 12345, 1459048620420001)
        self._test_next("2015-11-13 09:11:23.42", "Europe/Kyiv", 12345, 1447398683420000)
        # systemd-analyze calendar only reports next elapsed with second precision:
        # expressions with fractional seconds repetition will be rounded down to the
        # nearest whole second.
        #self._test_next("2015-11-13 09:11:23.42/1.77", "Europe/Kyiv", 1447398683420000, 1447398685190000)
        #self._test_next("2015-11-13 09:11:23.42/1.77", "Europe/Kyiv", 1447398683419999, 1447398683420000)
        self._test_next("Sun 16:00:00", "Europe/Berlin", 1456041600123456, 1456066800000000)
        self._test_next("*-04-31", "", 12345, -1)
        self._test_next("2016-02~01 UTC", "", 12345, 1456704000000000)
        self._test_next("Mon 2017-05~01..07 UTC", "", 12345, 1496016000000000)
        self._test_next("Mon 2017-05~07/1 UTC", "", 12345, 1496016000000000)
        self._test_next("*-*-01/5 04:00:00 UTC", "", 1646010000000000, 1646107200000000)
        self._test_next("*-01/7-01 04:00:00 UTC", "", 1664607600000000, 1672545600000000)
        self._test_next("2017-08-06 9,11,13,15,17:00 UTC", "", 1502029800000000, 1502031600000000)
        self._test_next("2017-08-06 9..17/2:00 UTC", "", 1502029800000000, 1502031600000000)
        self._test_next("2016-12-* 3..21/6:00 UTC", "", 1482613200000001, 1482634800000000)
        self._test_next("2017-09-24 03:30:00 Pacific/Auckland", "", 12345, 1506177000000000)
        # Due to daylight saving time - 2017-09-24 02:30:00 does not exist
        self._test_next("2017-09-24 02:30:00 Pacific/Auckland", "", 12345, -1)
        self._test_next("2017-04-02 02:30:00 Pacific/Auckland", "", 12345, 1491053400000000)
        # Confirm that even though it's a time change here (backward) 02:30 happens only once
        self._test_next("2017-04-02 02:30:00 Pacific/Auckland", "", 1491053400000000, -1)
        self._test_next("2017-04-02 03:30:00 Pacific/Auckland", "", 12345, 1491060600000000)
        # Confirm that timezones in the Spec work regardless of current timezone
        self._test_next("2017-09-09 20:42:00 Pacific/Auckland", "", 12345, 1504946520000000)
        self._test_next("2017-09-09 20:42:00 Pacific/Auckland", "Europe/Kyiv", 12345, 1504946520000000)
        # Check that we don't start looping if mktime() moves us backwards
        self._test_next("Sun *-*-* 01:00:00 Europe/Dublin", "", 1616412478000000, 1617494400000000)
        self._test_next("Sun *-*-* 01:00:00 Europe/Dublin", "IST", 1616412478000000, 1617494400000000)

