"""@LessonRepository Protocol backing ./services.py, per ../architecture.sdd."""

from datetime import date, time
from typing import Protocol

from .domain import Lesson


class LessonRepository(Protocol):
    def get(self, lesson_id: int) -> Lesson | None: ...
    def list_for_realization(self, course_realization_id: int) -> list[Lesson]: ...
    def list_for_range(self, start: date, end: date) -> list[Lesson]: ...
    def add(
        self,
        course_realization_id: int,
        lesson_date: date,
        start_time: time,
        end_time: time,
        topic: str,
        notes: str,
    ) -> Lesson: ...
    def update(
        self,
        lesson_id: int,
        lesson_date: date,
        start_time: time,
        end_time: time,
        topic: str,
        notes: str,
    ) -> Lesson: ...
    def delete(self, lesson_id: int) -> None: ...
