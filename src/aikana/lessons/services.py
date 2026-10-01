"""@LessonRepository-backed use cases, per ./lessons.sdd."""

from datetime import date, time

from .domain import Lesson
from .ports import LessonRepository


class LessonService:
    def __init__(self, repo: LessonRepository) -> None:
        self.repo = repo

    def list_lessons_for_realization(self, course_realization_id: str) -> list[Lesson]:
        return self.repo.list_for_realization(course_realization_id)

    def list_lessons_for_range(self, start: date, end: date) -> list[Lesson]:
        return self.repo.list_for_range(start, end)

    def add_lesson(
        self,
        course_realization_id: str,
        lesson_date: date,
        start_time: time,
        end_time: time,
        topic: str,
        notes: str,
    ) -> Lesson:
        return self.repo.add(course_realization_id, lesson_date, start_time, end_time, topic, notes)

