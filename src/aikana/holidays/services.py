"""@HolidayRepository-backed use cases, per ./holidays.sdd."""

from datetime import date

import holidays as public_holidays

from .domain import Holiday
from .ports import HolidayRepository


class InvalidHolidayError(Exception):
    pass


class DuplicateHolidayError(Exception):
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
        self._reject_duplicate(holiday_date)
        return self.repo.add(holiday_date, self._validated_title(title))

    def update_holiday(self, holiday_id: int | None, holiday_date: date, title: str) -> Holiday:
        existing = self.get_holiday(holiday_id)
        if existing is None:
            raise UnknownHolidayError(f"No Holiday with id {holiday_id!r}.")
        self._reject_duplicate(holiday_date, ignore_id=existing.id)
        return self.repo.update(existing.id, holiday_date, self._validated_title(title))

    def delete_holiday(self, holiday_id: int | None) -> None:
        existing = self.get_holiday(holiday_id)
        if existing is None:
            raise UnknownHolidayError(f"No Holiday with id {holiday_id!r}.")
        self.repo.delete(existing.id)

    def create_defaults_for_range(self, start: date, end: date) -> list[Holiday]:
        """The Finnish public holidays inside `start`..`end`, skipping a date that already holds a Holiday.

        The library's language is pinned to `fi` rather than left to the host locale, so the stored titles do not
        depend on the container's environment, per ./holidays.sdd.
        """
        existing = {holiday.date for holiday in self.repo.list_for_range(start, end)}
        added = []
        for year in range(start.year, end.year + 1):
            for holiday_date, title in public_holidays.Finland(years=year, language="fi").items():
                if start <= holiday_date <= end and holiday_date not in existing:
                    added.append(self.add_holiday(holiday_date, title))
        return added

    @staticmethod
    def _validated_title(title: str) -> str:
        title = title.strip()
        if not title:
            raise InvalidHolidayError("A Holiday needs a non-empty title.")
        return title

    def _reject_duplicate(self, holiday_date: date, ignore_id: int | None = None) -> None:
        """A date carries at most one Holiday, so a titled day never depends on which row is read last."""
        if any(
            holiday.id != ignore_id and holiday.date == holiday_date
            for holiday in self.repo.list_for_range(holiday_date, holiday_date)
        ):
            raise DuplicateHolidayError(f"{holiday_date.isoformat()} already has a Holiday.")
