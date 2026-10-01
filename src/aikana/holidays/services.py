"""Placeholder stand-in for a @HolidayRepository-backed service, per ./holidays.sdd Tasks."""

from datetime import date

from .domain import Holiday

_PLACEHOLDER_HOLIDAYS = [
    Holiday(id="holiday-1", date=date(2026, 12, 6), title="Independence Day"),
]


def list_holidays_for_range(start: date, end: date) -> list[Holiday]:
    return [holiday for holiday in _PLACEHOLDER_HOLIDAYS if start <= holiday.date <= end]
