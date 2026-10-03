"""Adapter implementing @LessonRepository using `fastlite`, per ../architecture.sdd."""

from datetime import date, time
from uuid import uuid4

from fastlite import Database

from .domain import Lesson


def _to_domain(row: dict) -> Lesson:
    return Lesson(
        id=row["id"],
        course_realization_id=row["course_realization_id"],
        date=date.fromisoformat(row["date"]),
        start_time=time.fromisoformat(row["start_time"]),
        end_time=time.fromisoformat(row["end_time"]),
        topic=row["topic"],
        notes=row["notes"],
    )


class SqliteLessonRepository:
    def __init__(self, db: Database) -> None:
        self._table = db.t.lessons
        self._table.create(
            columns={
                "id": str,
                "course_realization_id": str,
                "date": str,
                "start_time": str,
                "end_time": str,
                "topic": str,
                "notes": str,
            },
            pk="id",
            if_not_exists=True,
        )

    def list_for_realization(self, course_realization_id: str) -> list[Lesson]:
        rows = self._table(
            where="course_realization_id = ?", where_args=[course_realization_id], order_by="date, start_time"
        )
        return [_to_domain(row) for row in rows]

    def list_for_range(self, start: date, end: date) -> list[Lesson]:
        rows = self._table(
            where="date >= ? and date <= ?",
            where_args=[start.isoformat(), end.isoformat()],
            order_by="date, start_time",
        )
        return [_to_domain(row) for row in rows]

    def add(
        self,
        course_realization_id: str,
        lesson_date: date,
        start_time: time,
        end_time: time,
        topic: str,
        notes: str,
    ) -> Lesson:
        row = self._table.insert(
            {
                "id": uuid4().hex,
                "course_realization_id": course_realization_id,
                "date": lesson_date.isoformat(),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "topic": topic,
                "notes": notes,
            }
        )
        return _to_domain(row)

    def delete_for_realization(self, course_realization_id: str) -> None:
        # `fastlite`'s delete addresses one primary key at a time, so the realization's Lessons are read and
        # removed by id.
        for lesson in self.list_for_realization(course_realization_id):
            self._table.delete(lesson.id)
