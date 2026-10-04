"""@HolidayRepository-backed use cases, per ./holidays.sdd."""

from datetime import date

from .domain import Holiday
from .ports import HolidayRepository


class InvalidHolidayError(Exception):
    pass


class UnknownHolidayError(Exception):
    pass


class HolidayService:
    def __init__(self, repo: HolidayRepository) -> None:
        self.repo = repo

    def get_holiday(self, holiday_id: int | None) -> Holiday | None:
        return self.repo.get(holiday_id) if holiday_id is not None else None

    def list_holidays_for_range(self, start: date, end: date) -> list[Holiday]:
        return self.repo.list_for_range(start, end)

    def add_holiday(self, holiday_date: date, title: str) -> Holiday:
        return self.repo.add(holiday_date, self._validated_title(title))

    def update_holiday(self, holiday_id: int | None, holiday_date: date, title: str) -> Holiday:
        existing = self.get_holiday(holiday_id)
        if existing is None:
            raise UnknownHolidayError(f"No Holiday with id {holiday_id!r}.")
        return self.repo.update(existing.id, holiday_date, self._validated_title(title))

    def delete_holiday(self, holiday_id: int | None) -> None:
        existing = self.get_holiday(holiday_id)
        if existing is None:
            raise UnknownHolidayError(f"No Holiday with id {holiday_id!r}.")
        self.repo.delete(existing.id)

    @staticmethod
    def _validated_title(title: str) -> str:
        title = title.strip()
        if not title:
            raise InvalidHolidayError("A Holiday needs a non-empty title.")
        return title
