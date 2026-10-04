"""Adapter implementing @SemesterRepository using `fastlite`, per ../architecture.sdd."""

from fastlite import Database

from .domain import Semester, Term


def _to_domain(row: dict) -> Semester:
    return Semester(id=row["id"], year=row["year"], term=row["term"])


class SqliteSemesterRepository:
    def __init__(self, db: Database) -> None:
        self._table = db.t.semesters
        self._table.create(
            columns={"id": int, "year": int, "term": str},
            pk="id",
            if_not_exists=True,
            not_null=["year", "term"],
            strict=True,
        )
        # @SemesterService rejects a duplicate year+term; this index is the database-level backstop.
        self._table.create_index(["year", "term"], unique=True, if_not_exists=True)

    def list(self) -> list[Semester]:
        # `spring` starts the calendar year and `fall` ends it, so plain `term` ordering would put fall first.
        return [
            _to_domain(row)
            for row in self._table(order_by="year, CASE term WHEN 'spring' THEN 0 ELSE 1 END")
        ]

    def get(self, semester_id: int) -> Semester | None:
        row = self._table.get(semester_id, default=None)
        return _to_domain(row) if row else None

    def add(self, year: int, term: Term) -> Semester:
        row = self._table.insert({"year": year, "term": term})
        return _to_domain(row)

    def delete(self, semester_id: int) -> None:
        # The `course_realizations` and `no_teach_weeks` foreign keys cascade to the Semester's
        # realizations (and through them its Lessons) and its NoTeachWeeks.
        self._table.delete(semester_id)
