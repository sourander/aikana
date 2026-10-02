"""@HolidayRepository-backed use cases, per ./holidays.sdd."""

from datetime import date

from .domain import Holiday
from .ports import HolidayRepository


class InvalidHolidayError(Exception):
    pass


class HolidayService:
    def __init__(self, repo: HolidayRepository) -> None:
        self.repo = repo

    def list_holidays_for_range(self, start: date, end: date) -> list[Holiday]:
        return self.repo.list_for_range(start, end)

    def add_holiday(self, holiday_date: date, title: str) -> Holiday:
        title = title.strip()
        if not title:
            raise InvalidHolidayError("A Holiday needs a non-empty title.")
        return self.repo.add(holiday_date, title)

