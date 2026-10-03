"""@SemesterRepository Protocol backing ./services.py, per ../architecture.sdd."""

from typing import Protocol

from .domain import Semester, Term


class SemesterRepository(Protocol):
    def list(self) -> list[Semester]: ...
    def get(self, semester_id: int) -> Semester | None: ...
    def add(self, year: int, term: Term) -> Semester: ...
