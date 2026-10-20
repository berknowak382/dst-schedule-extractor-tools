"""Core logic for finding daylight saving time transitions.

This module uses the standard-library ``zoneinfo`` module (Python 3.9+)
to probe a timezone's UTC offset at 12:00 local time on every day in a
given range.  A change in the UTC offset between consecutive days marks
a transition day.

Why 12:00 local time?  Transitions typically happen around 01:00 or
02:00 or 03:00 local time, and on the transition day the clock may jump
forward (gap) or backward (overlap).  Sampling at noon avoids landing
in a gap or overlap and gives a stable offset that we can attribute to
that calendar day.

Design choice and limitation: the returned ``DSTTransition`` carries a
date, the UTC offset before the transition, the UTC offset after, and a
flag indicating whether it is a "spring forward" (clocks move ahead,
shorter day) or "fall back" (clocks move behind, repeated hour).  We
don't report the exact wall-clock moment of the change because that
information is not readily and reliably available from ``zoneinfo``
without re-implementing zic rules.  For schedule planning, the date and
direction of the change are usually what is needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class DSTTransition:
    """A single daylight saving time transition day.

    Attributes
    ----------
    date:
        The calendar day on which the UTC offset changes (sampled at
        local noon of that day).
    offset_before:
        UTC offset (as a ``timedelta``) on the day before the transition.
    offset_after:
        UTC offset (as a ``timedelta``) on the transition day itself.
    spring_forward:
        ``True`` if the clock moves ahead (spring forward, gap); ``False``
        if the clock moves behind (fall back, overlap).
    """

    date: date
    offset_before: timedelta
    offset_after: timedelta
    spring_forward: bool

    def __post_init__(self) -> None:
        # A transition must always involve a non-zero change.
        if self.offset_before == self.offset_after:
            raise ValueError(
                "A DSTTransition requires distinct offsets; "
                "offset_before equals offset_after."
            )


# --- Internal helpers ----------------------------------------------------


def _noon_offset(d: date, tz: ZoneInfo) -> timedelta:
    """Return the UTC offset at local noon of *d* in timezone *tz*.

    We use ``datetime(d.year, d.month, d.day, 12, 0, tzinfo=tz)``.  This
    is a PEP 495 aware construction, so it picks the later offset in an
    overlap and the first valid wall time in a gap — but noon is almost
    never inside a gap or overlap, so the result is stable.
    """
    return datetime(d.year, d.month, d.day, 12, 0, tzinfo=tz).utcoffset()


def _iter_days(start: date, end: date):
    """Yield every ``date`` from *start* to *end* inclusive."""
    if end < start:
        return
    cur = start
    one_day = timedelta(days=1)
    while cur <= end:
        yield cur
        cur += one_day


# --- Public API ----------------------------------------------------------


def get_dst_schedule(timezone_name: str, start: date, end: date):
    """Return a list of ``DSTTransition`` objects in [*start*, *end*].

    Parameters
    ----------
    timezone_name:
        An IANA timezone name understood by ``zoneinfo``, e.g.
        ``"America/New_York"`` or ``"Europe/London"``.
    start, end:
        Inclusive calendar dates that bound the search.

    Returns
    -------
    list[DSTTransition]
        Chronologically ordered transitions whose change occurs on a day
        within [*start*, *end*].  If *start* equals *end* the result is
        always empty because we need two consecutive days to detect a
        change.
    """
    tz = ZoneInfo(timezone_name)
    transitions: list[DSTTransition] = []

    # We need the offset of the day before ``start`` to decide whether
    # ``start`` itself is a transition day, so we begin one day earlier
    # in the probe loop.
    prev = start - timedelta(days=1)
    prev_offset = _noon_offset(prev, tz)

    for cur in _iter_days(start, end):
        cur_offset = _noon_offset(cur, tz)
        if cur_offset != prev_offset:
            spring = cur_offset > prev_offset
            transitions.append(
                DSTTransition(
                    date=cur,
                    offset_before=prev_offset,
                    offset_after=cur_offset,
                    spring_forward=spring,
                )
            )
        prev_offset = cur_offset

    return transitions


def find_transitions_in_range(
    timezone_name: str, year: int, month: int, day: int
):
    """Return transitions in a 365-day window starting at the given date.

    This is a convenience wrapper for ``get_dst_schedule`` that builds a
    date from the given year/month/day and searches exactly one calendar
    year forward (inclusive of both endpoints).

    Raises
    ------
    ValueError
        If the date components are invalid (e.g. month=13) or if no
        timezone data is found for ``timezone_name``.
    """
    start = date(year, month, day)
    end = start.replace(year=year + 1)
    return get_dst_schedule(timezone_name, start, end)
