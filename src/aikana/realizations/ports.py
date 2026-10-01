"""@CourseRealizationRepository Protocol backing ./services.py, per ../architecture.sdd."""

from typing import Protocol

from .domain import CourseRealization


class CourseRealizationRepository(Protocol):
    def list_for_semester(self, semester_id: str) -> list[CourseRealization]: ...
    def get(self, realization_id: str) -> CourseRealization | None: ...
    def add(self, course_id: str, semester_id: str, group: str) -> CourseRealization: ...
