"""@LessonRepository-backed use cases, per ./lessons.sdd."""

from datetime import date, time

from ..no_teach_weeks.services import NoTeachWeekService
from ..realizations.ports import CourseRealizationRepository
from .domain import Lesson
from .ports import LessonRepository


class UnknownRealizationError(Exception):
    pass


class InvalidLessonError(Exception):
    pass


class LessonService:
    def __init__(
        self,
        repo: LessonRepository,
        realization_repo: CourseRealizationRepository,
        no_teach_week_service: NoTeachWeekService,
    ) -> None:
        self.repo = repo
        # ../realizations/realizations.sdd's port, used only to validate referenced ids, per ../architecture.sdd.
        self.realization_repo = realization_repo
        # ../no_teach_weeks/no_teach_weeks.sdd's service, used only to reject a date inside a NoTeachWeek.
        self.no_teach_week_service = no_teach_week_service

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
        realization = self.realization_repo.get(course_realization_id)
        if realization is None:
            raise UnknownRealizationError(f"No CourseRealization with id {course_realization_id!r}.")
        blocked = self.no_teach_week_service.titles_by_teaching_day(realization.semester_id)
        if lesson_date in blocked:
            raise InvalidLessonError(f"{lesson_date.isoformat()} falls inside a NoTeachWeek.")
        topic = topic.strip()
        if not topic:
            raise InvalidLessonError("A Lesson needs a non-empty topic.")
        if end_time <= start_time:
            raise InvalidLessonError("A Lesson's end time must be later than its start time.")
        return self.repo.add(course_realization_id, lesson_date, start_time, end_time, topic, notes)
