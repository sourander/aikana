"""Adapter implementing @CourseRealizationRepository using `fastlite`, per ../architecture.sdd."""

from uuid import uuid4

from fastlite import Database

from .domain import CourseRealization


def _to_domain(row: dict) -> CourseRealization:
    return CourseRealization(
        id=row["id"],
        course_id=row["course_id"],
        semester_id=row["semester_id"],
        group=row["group"],
    )


class SqliteCourseRealizationRepository:
    def __init__(self, db: Database) -> None:
        self._table = db.t.course_realizations
        self._table.create(
            columns={"id": str, "course_id": str, "semester_id": str, "group": str},
            pk="id",
            if_not_exists=True,
        )

    def list_for_course(self, course_id: str) -> list[CourseRealization]:
        rows = self._table(where="course_id = ?", where_args=[course_id])
        return [_to_domain(row) for row in rows]

    def list_for_semester(self, semester_id: str) -> list[CourseRealization]:
        rows = self._table(where="semester_id = ?", where_args=[semester_id])
        return [_to_domain(row) for row in rows]

    def get(self, realization_id: str) -> CourseRealization | None:
        row = self._table.get(realization_id, default=None)
        return _to_domain(row) if row else None

    def add(self, course_id: str, semester_id: str, group: str) -> CourseRealization:
        row = self._table.insert(
            {"id": uuid4().hex, "course_id": course_id, "semester_id": semester_id, "group": group}
        )
        return _to_domain(row)

    def update(
        self, realization_id: str, course_id: str, semester_id: str, group: str
    ) -> CourseRealization:
        row = self._table.update(
            {
                "id": realization_id,
                "course_id": course_id,
                "semester_id": semester_id,
                "group": group,
            }
        )
        return _to_domain(row)

    def delete(self, realization_id: str) -> None:
        self._table.delete(realization_id)
