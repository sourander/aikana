"""@LessonRepository-backed use cases, per ./lessons.sdd."""

from datetime import date, time

from ..realizations.ports import CourseRealizationRepository
from .domain import Lesson
from .ports import LessonRepository


class UnknownRealizationError(Exception):
    pass


class InvalidLessonError(Exception):
    pass


class LessonService:
    def __init__(self, repo: LessonRepository, realization_repo: CourseRealizationRepository) -> None:
        self.repo = repo
        # ../realizations/realizations.sdd's port, used only to validate referenced ids, per ../architecture.sdd.
        self.realization_repo = realization_repo

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
        if self.realization_repo.get(course_realization_id) is None:
            raise UnknownRealizationError(f"No CourseRealization with id {course_realization_id!r}.")
        topic = topic.strip()
        if not topic:
            raise InvalidLessonError("A Lesson needs a non-empty topic.")
        if end_time <= start_time:
            raise InvalidLessonError("A Lesson's end time must be later than its start time.")
        return self.repo.add(course_realization_id, lesson_date, start_time, end_time, topic, notes)
