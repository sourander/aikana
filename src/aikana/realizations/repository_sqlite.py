"""Adapter implementing @CourseRealizationRepository using `fastlite`, per ../architecture.sdd."""

from fastlite import Database

from .domain import CourseRealization


def _to_domain(row: dict) -> CourseRealization:
    return CourseRealization(
        id=row["id"],
        course_id=row["course_id"],
        semester_id=row["semester_id"],
        # The column is `group_label` because `group` is a reserved SQL keyword; the domain keeps `group`.
        group=row["group_label"],
    )


class SqliteCourseRealizationRepository:
    def __init__(self, db: Database) -> None:
        self._table = db.t.course_realizations
        self._table.create(
            columns={"id": int, "course_id": int, "semester_id": int, "group_label": str},
            pk="id",
            if_not_exists=True,
            not_null=["course_id", "semester_id", "group_label"],
            strict=True,
            # Removing a Course removes its realizations through the `course_id` constraint; removing a
            # Semester removes its realizations through the `semester_id` one.
            foreign_keys=[("course_id", "courses", "id"), ("semester_id", "semesters", "id")],
        )
        self._table.create_index(["course_id"], if_not_exists=True)
        self._table.create_index(["semester_id"], if_not_exists=True)

    def list_for_course(self, course_id: int) -> list[CourseRealization]:
        rows = self._table(where="course_id = ?", where_args=[course_id])
        return [_to_domain(row) for row in rows]

    def list_for_semester(self, semester_id: int) -> list[CourseRealization]:
        rows = self._table(where="semester_id = ?", where_args=[semester_id])
        return [_to_domain(row) for row in rows]

    def get(self, realization_id: int) -> CourseRealization | None:
        row = self._table.get(realization_id, default=None)
        return _to_domain(row) if row else None

    def add(self, course_id: int, semester_id: int, group: str) -> CourseRealization:
        row = self._table.insert(
            {"course_id": course_id, "semester_id": semester_id, "group_label": group}
        )
        return _to_domain(row)

    def update(
        self, realization_id: int, course_id: int, semester_id: int, group: str
    ) -> CourseRealization:
        row = self._table.update(
            {
                "id": realization_id,
                "course_id": course_id,
                "semester_id": semester_id,
                "group_label": group,
            }
        )
        return _to_domain(row)

    def delete(self, realization_id: int) -> None:
        # The `lessons` foreign key cascades to the realization's Lessons.
        self._table.delete(realization_id)
