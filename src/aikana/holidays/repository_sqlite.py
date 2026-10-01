"""Adapter implementing @HolidayRepository using `fastlite`, per ../architecture.sdd."""

from datetime import date
from uuid import uuid4

from ..shared.db import get_db
from .domain import Holiday


def _to_domain(row: dict) -> Holiday:
    return Holiday(id=row["id"], date=date.fromisoformat(row["date"]), title=row["title"])


class SqliteHolidayRepository:
    def __init__(self) -> None:
        self._table = get_db().t.holidays
        self._table.create(columns={"id": str, "date": str, "title": str}, pk="id", if_not_exists=True)

    def list_for_range(self, start: date, end: date) -> list[Holiday]:
        rows = self._table(
            where="date >= ? and date <= ?",
            where_args=[start.isoformat(), end.isoformat()],
            order_by="date",
        )
        return [_to_domain(row) for row in rows]

    def add(self, holiday_date: date, title: str) -> Holiday:
        row = self._table.insert({"id": uuid4().hex, "date": holiday_date.isoformat(), "title": title})
        return _to_domain(row)
