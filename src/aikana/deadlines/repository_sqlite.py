"""Adapter implementing @DeadlineRepository using `fastlite`, per ../architecture.sdd."""

from datetime import date

from fastlite import Database

from .domain import Deadline


def _to_domain(row: dict) -> Deadline:
    return Deadline(
        id=row["id"],
        course_realization_id=row["course_realization_id"],
        date=date.fromisoformat(row["date"]),
        title=row["title"],
    )


class SqliteDeadlineRepository:
    def __init__(self, db: Database) -> None:
        self._table = db.t.deadlines
        self._table.create(
            columns={
                "id": int,
                "course_realization_id": int,
                "date": str,
                "title": str,
            },
            pk="id",
            if_not_exists=True,
            not_null=["course_realization_id", "date", "title"],
            strict=True,
            # Removing a CourseRealization removes its Deadlines through this constraint, per ./deadlines.sdd.
            foreign_keys=[("course_realization_id", "course_realizations", "id")],
        )
        # No uniqueness rule: several Deadlines may share one date, since a realization can owe more than one thing
        # the same day, per ./deadlines.sdd.
        self._table.create_index(["course_realization_id", "date"], if_not_exists=True)
        self._table.create_index(["date"], if_not_exists=True)

    def get(self, deadline_id: int) -> Deadline | None:
        row = self._table.get(deadline_id, default=None)
        return _to_domain(row) if row else None

    def list_for_realization(self, course_realization_id: int) -> list[Deadline]:
        rows = self._table(
            where="course_realization_id = ?", where_args=[course_realization_id], order_by="date, id"
        )
        return [_to_domain(row) for row in rows]

    def list_for_range(self, start: date, end: date) -> list[Deadline]:
        rows = self._table(
            where="date >= ? and date <= ?",
            where_args=[start.isoformat(), end.isoformat()],
            order_by="date, id",
        )
        return [_to_domain(row) for row in rows]

    def add(self, course_realization_id: int, deadline_date: date, title: str) -> Deadline:
        row = self._table.insert(
            {
                "course_realization_id": course_realization_id,
                "date": deadline_date.isoformat(),
                "title": title,
            }
        )
        return _to_domain(row)

    def update(self, deadline_id: int, deadline_date: date, title: str) -> Deadline:
        row = self._table.update(
            {"id": deadline_id, "date": deadline_date.isoformat(), "title": title}
        )
        return _to_domain(row)

    def delete(self, deadline_id: int) -> None:
        self._table.delete(deadline_id)