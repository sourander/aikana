"""Adapter implementing @CourseRepository using `fastlite`, per ../architecture.sdd."""

from uuid import uuid4

from fastlite import Database

from .domain import Course


def _to_domain(row: dict) -> Course:
    return Course(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        ects_credits=row["ects_credits"],
    )


class SqliteCourseRepository:
    def __init__(self, db: Database) -> None:
        self._table = db.t.courses
        self._table.create(
            columns={"id": str, "name": str, "description": str, "ects_credits": int},
            pk="id",
            if_not_exists=True,
        )

    def list(self) -> list[Course]:
        return [_to_domain(row) for row in self._table(order_by="name")]

    def get(self, course_id: str) -> Course | None:
        row = self._table.get(course_id, default=None)
        return _to_domain(row) if row else None

    def add(self, name: str, description: str, ects_credits: int) -> Course:
        row = self._table.insert({"id": uuid4().hex, "name": name, "description": description, "ects_credits": ects_credits})
        return _to_domain(row)

    def update(self, course_id: str, name: str, description: str, ects_credits: int) -> Course:
        row = self._table.update(
            {"id": course_id, "name": name, "description": description, "ects_credits": ects_credits}
        )
        return _to_domain(row)

    def delete(self, course_id: str) -> None:
        self._table.delete(course_id)
