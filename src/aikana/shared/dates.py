"""The shared Europe/Helsinki date policy, per ../aikana.sdd and ./shared.sdd."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TIME_ZONE = ZoneInfo("Europe/Helsinki")

# Weeks start on Monday in ../aikana.sdd, so every rendered week and month grid starts here.
MONDAY_FIRST_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def today() -> date:
    """The current date in `Europe/Helsinki`, regardless of the host's time zone."""
    return datetime.now(TIME_ZONE).date()


def format_date(value: date) -> str:
    """A calendar date in the European `d.m.yyyy` form, for example `2.10.2026`."""
    return f"{value.day}.{value.month}.{value.year}"


def month_grid(value: date) -> list[list[date | None]]:
    """The month containing `value` as Monday-first weeks of seven days.

    Each week starts on its Monday and the leading and trailing days of the neighbouring months pad the first and last
    week as `None`, so the grid always has whole Monday-to-Sunday weeks.
    """
    first = value.replace(day=1)
    last = (first + timedelta(days=31)).replace(day=1) - timedelta(days=1)
    days = [first + timedelta(days=offset) for offset in range((last - first).days + 1)]
    padded = [None] * first.weekday() + days
    padded += [None] * (-len(padded) % 7)
    return [padded[start : start + 7] for start in range(0, len(padded), 7)]
