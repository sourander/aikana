"""Adapter implementing @LessonRepository using `fastlite`, per ../architecture.sdd."""

from datetime import date, time

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
                "id": int,
                "course_realization_id": int,
                "date": str,
                "start_time": str,
                "end_time": str,
                "topic": str,
                "notes": str,
            },
            pk="id",
            if_not_exists=True,
            not_null=["course_realization_id", "date", "start_time", "end_time", "topic", "notes"],
            strict=True,
            # Removing a CourseRealization removes its Lessons through this constraint, per
            # ../realizations/realizations.sdd.
            foreign_keys=[("course_realization_id", "course_realizations", "id")],
        )
        # @LessonService allows one Lesson per date and CourseRealization; this index is the backstop.
        self._table.create_index(["course_realization_id", "date"], unique=True, if_not_exists=True)
        self._table.create_index(["date"], if_not_exists=True)

    def get(self, lesson_id: int) -> Lesson | None:
        row = self._table.get(lesson_id, default=None)
        return _to_domain(row) if row else None

    def list_for_realization(self, course_realization_id: int) -> list[Lesson]:
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
        course_realization_id: int,
        lesson_date: date,
        start_time: time,
        end_time: time,
        topic: str,
        notes: str,
    ) -> Lesson:
        row = self._table.insert(
            {
                "course_realization_id": course_realization_id,
                "date": lesson_date.isoformat(),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "topic": topic,
                "notes": notes,
            }
        )
        return _to_domain(row)

    def update(
        self,
        lesson_id: int,
        lesson_date: date,
        start_time: time,
        end_time: time,
        topic: str,
        notes: str,
    ) -> Lesson:
        row = self._table.update(
            {
                "id": lesson_id,
                "date": lesson_date.isoformat(),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "topic": topic,
                "notes": notes,
            }
        )
        return _to_domain(row)

    def delete(self, lesson_id: int) -> None:
        self._table.delete(lesson_id)
