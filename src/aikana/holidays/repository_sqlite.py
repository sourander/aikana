"""Adapter implementing @HolidayRepository using `fastlite`, per ../architecture.sdd."""

from datetime import date

from fastlite import Database

from .domain import Holiday


def _to_domain(row: dict) -> Holiday:
    return Holiday(id=row["id"], date=date.fromisoformat(row["date"]), title=row["title"])


class SqliteHolidayRepository:
    def __init__(self, db: Database) -> None:
        self._table = db.t.holidays
        self._table.create(
            columns={"id": int, "date": str, "title": str},
            pk="id",
            if_not_exists=True,
            not_null=["date", "title"],
            strict=True,
        )
        # A date carries at most one Holiday, per ./holidays.sdd. An earlier database may already hold a
        # non-unique index of the same name, which `if_not_exists` would silently keep, so it is dropped first.
        db.execute("DROP INDEX IF EXISTS [idx_holidays_date]")
        self._table.create_index(["date"], unique=True, if_not_exists=True)

    def get(self, holiday_id: int) -> Holiday | None:
        row = self._table.get(holiday_id, default=None)
        return _to_domain(row) if row else None

    def list_for_range(self, start: date, end: date) -> list[Holiday]:
        rows = self._table(
            where="date >= ? and date <= ?",
            where_args=[start.isoformat(), end.isoformat()],
            order_by="date",
        )
        return [_to_domain(row) for row in rows]

    def add(self, holiday_date: date, title: str) -> Holiday:
        row = self._table.insert({"date": holiday_date.isoformat(), "title": title})
        return _to_domain(row)

    def update(self, holiday_id: int, holiday_date: date, title: str) -> Holiday:
        row = self._table.update({"id": holiday_id, "date": holiday_date.isoformat(), "title": title})
        return _to_domain(row)

    def delete(self, holiday_id: int) -> None:
        self._table.delete(holiday_id)
