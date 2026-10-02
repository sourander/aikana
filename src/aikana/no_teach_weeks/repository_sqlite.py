"""Adapter implementing @NoTeachWeekRepository using `fastlite`, per ../architecture.sdd."""

from datetime import date
from uuid import uuid4

from fastlite import Database

from .domain import NoTeachWeek


def _to_domain(row: dict) -> NoTeachWeek:
    return NoTeachWeek(
        id=row["id"],
        semester_id=row["semester_id"],
        week_number=row["week_number"],
        week_start=date.fromisoformat(row["week_start"]),
        title=row["title"],
    )


class SqliteNoTeachWeekRepository:
    def __init__(self, db: Database) -> None:
        self._table = db.t.no_teach_weeks
        self._table.create(
            columns={
                "id": str,
                "semester_id": str,
                "week_number": int,
                "week_start": str,
                "title": str,
            },
            pk="id",
            if_not_exists=True,
        )

    def list_for_semester(self, semester_id: str) -> list[NoTeachWeek]:
        rows = self._table(
            where="semester_id = ?", where_args=[semester_id], order_by="week_number"
        )
        return [_to_domain(row) for row in rows]

    def get(self, no_teach_week_id: str) -> NoTeachWeek | None:
        row = self._table.get(no_teach_week_id, default=None)
        return _to_domain(row) if row else None

    def add(self, semester_id: str, week_number: int, week_start: date, title: str) -> NoTeachWeek:
        row = self._table.insert(
            {
                "id": uuid4().hex,
                "semester_id": semester_id,
                "week_number": week_number,
                "week_start": week_start.isoformat(),
                "title": title,
            }
        )
        return _to_domain(row)

    def update(self, no_teach_week_id: str, week_number: int, week_start: date, title: str) -> NoTeachWeek:
        row = self._table.update(
            {
                "id": no_teach_week_id,
                "week_number": week_number,
                "week_start": week_start.isoformat(),
                "title": title,
            }
        )
        return _to_domain(row)

    def delete(self, no_teach_week_id: str) -> None:
        self._table.delete(no_teach_week_id)