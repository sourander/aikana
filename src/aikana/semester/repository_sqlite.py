"""Adapter implementing @SemesterRepository using `fastlite`, per ../architecture.sdd."""

from uuid import uuid4

from ..shared.db import get_db
from .domain import Semester, Term


def _to_domain(row: dict) -> Semester:
    return Semester(id=row["id"], year=row["year"], term=row["term"])


class SqliteSemesterRepository:
    def __init__(self) -> None:
        self._table = get_db().t.semesters
        self._table.create(
            columns={"id": str, "year": int, "term": str},
            pk="id",
            if_not_exists=True,
        )

    def list(self) -> list[Semester]:
        return [_to_domain(row) for row in self._table(order_by="year, term")]

    def get(self, semester_id: str) -> Semester | None:
        row = self._table.get(semester_id, default=None)
        return _to_domain(row) if row else None

    def add(self, year: int, term: Term) -> Semester:
        row = self._table.insert({"id": uuid4().hex, "year": year, "term": term})
        return _to_domain(row)
