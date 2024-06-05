# Copyright (C) 2023 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>
#
# tests/__init__.py - Snapshot Manager
#
# This file is part of the snapm project.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions
# of the GNU General Public License v.2.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
import os
from os.path import abspath, join
import time

os.environ["TZ"] = "UTC"
time.tzset()

BOOT_ROOT_TEST = join(os.getcwd(), "tests/boot")


class MockArgs(object):
    identifier = None
    debug = None
    name = None
    name_prefixes = False
    no_headings = False
    options = ""
    members = False
    sort = ""
    rows = False
    separator = None
    uuid = None
    verbose = 0
    version = False


def have_root():
    """Return ``True`` if the test suite is running as the root user,
    and ``False`` otherwise.
    """
    return os.geteuid() == 0 and os.getegid() == 0
