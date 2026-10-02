"""The shared Europe/Helsinki date policy, per ../aikana.sdd and ./shared.sdd."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

TIME_ZONE = ZoneInfo("Europe/Helsinki")


def today() -> date:
    """The current date in `Europe/Helsinki`, regardless of the host's time zone."""
    return datetime.now(TIME_ZONE).date()


def format_date(value: date) -> str:
    """A calendar date in the European `d.m.yyyy` form, for example `2.10.2026`."""
    return f"{value.day}.{value.month}.{value.year}"
