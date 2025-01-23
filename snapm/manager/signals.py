# Copyright (C) 2025 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>
#
# snapm/manager/signals.py - Snapshot Manager signal handling
#
# This file is part of the snapm project.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions
# of the GNU General Public License v.2.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
"""
Helpers for blocking and unblocking signal delivery.
"""
from signal import SIG_BLOCK, SIG_UNBLOCK, SIGINT, SIGTERM, pthread_sigmask
from functools import wraps
import logging

_log = logging.getLogger(__name__)
_log_debug = _log.debug

_to_block = {SIGINT, SIGTERM}


def block_signals():
    """
    Block termination signals before entering critical section.
    """
    _log_debug("Blocking termination signals %s", _to_block)
    pthread_sigmask(SIG_BLOCK, _to_block)


def unblock_signals():
    """
    Unblock and deliver termination signals after leaving critical section.
    """
    _log_debug("Unblocking termination signals %s", _to_block)
    pthread_sigmask(SIG_UNBLOCK, _to_block)


def suspend_signals(func):
    """
    Decorator to wrap functions that implement a critical section.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        block_signals()
        try:
            ret = func(*args, **kwargs)
        finally:
            unblock_signals()
        return ret

    return wrapper
