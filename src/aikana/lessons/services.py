"""@LessonRepository-backed use cases, per ./lessons.sdd."""

from datetime import date, time

from ..no_teach_weeks.services import NoTeachWeekService
from ..realizations.ports import CourseRealizationRepository
from ..shared import dates
from .domain import Lesson
from .ports import LessonRepository


class UnknownRealizationError(Exception):
    pass


class InvalidLessonError(Exception):
    pass


class UnknownLessonError(Exception):
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

    def get_lesson(self, lesson_id: str) -> Lesson | None:
        return self.repo.get(lesson_id) if lesson_id else None

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
        topic = self._validated_topic(
            realization.semester_id, course_realization_id, lesson_date, start_time, end_time, topic
        )
        return self.repo.add(course_realization_id, lesson_date, start_time, end_time, topic, notes)

    def update_lesson(
        self,
        lesson_id: str,
        lesson_date: date,
        start_time: time,
        end_time: time,
        topic: str,
        notes: str,
    ) -> Lesson:
        """Edits one Lesson in place; it stays in the CourseRealization it already belongs to."""
        existing = self.get_lesson(lesson_id)
        if existing is None:
            raise UnknownLessonError(f"No Lesson with id {lesson_id!r}.")
        realization = self.realization_repo.get(existing.course_realization_id)
        topic = self._validated_topic(
            realization.semester_id,
            existing.course_realization_id,
            lesson_date,
            start_time,
            end_time,
            topic,
            lesson_id,
        )
        return self.repo.update(lesson_id, lesson_date, start_time, end_time, topic, notes)

    def delete_lesson(self, lesson_id: str) -> None:
        """Removes one Lesson, leaving its CourseRealization and its other Lessons untouched."""
        if self.get_lesson(lesson_id) is None:
            raise UnknownLessonError(f"No Lesson with id {lesson_id!r}.")
        self.repo.delete(lesson_id)

    def _validated_topic(
        self,
        semester_id: str,
        course_realization_id: str,
        lesson_date: date,
        start_time: time,
        end_time: time,
        topic: str,
        lesson_id: str = "",
    ) -> str:
        """The checked topic every write shares; `lesson_id` excludes the Lesson being edited from the day check."""
        blocked = self.no_teach_week_service.titles_by_teaching_day(semester_id)
        if lesson_date in blocked:
            raise InvalidLessonError(f"{dates.format_date(lesson_date)} falls inside a NoTeachWeek.")
        topic = topic.strip()
        if not topic:
            raise InvalidLessonError("A Lesson needs a non-empty topic.")
        if end_time <= start_time:
            raise InvalidLessonError("A Lesson's end time must be later than its start time.")
        if self._claims_day(course_realization_id, lesson_date, lesson_id):
            raise InvalidLessonError(
                f"{dates.format_date(lesson_date)} already has a Lesson for this CourseRealization."
            )
        return topic

    def _claims_day(self, course_realization_id: str, lesson_date: date, lesson_id: str) -> bool:
        return any(
            lesson.date == lesson_date and lesson.id != lesson_id
            for lesson in self.repo.list_for_realization(course_realization_id)
        )

    def delete_lessons_for_realization(self, course_realization_id: str) -> None:
        """Removes every Lesson of a CourseRealization, used when that realization is removed."""
        self.repo.delete_for_realization(course_realization_id)
