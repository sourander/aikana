"""SDK-free adaptation of the feature services for the MCP tools, per ./mcp_server.sdd.

Everything here is plain Python: entities go out as JSON-compatible dicts, dates and times come in and go out as
ISO 8601 strings, and every feature service's validation or lookup failure is re-raised as the package-local
@McpError, so ./server.py has exactly one error type to map to the SDK's tool error.
"""

import hmac
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, time
from typing import TypedDict

from ..courses import services as course_services
from ..courses.domain import Course
from ..courses.services import CourseService
from ..deadlines import services as deadline_services
from ..deadlines.domain import Deadline
from ..deadlines.services import DeadlineService
from ..holidays import services as holiday_services
from ..holidays.domain import Holiday
from ..holidays.services import HolidayService
from ..lessons import services as lesson_services
from ..lessons.domain import Lesson
from ..lessons.services import LessonService
from ..no_teach_weeks import services as no_teach_week_services
from ..no_teach_weeks.domain import NoTeachWeek
from ..no_teach_weeks.services import NoTeachWeekService
from ..realizations import services as realization_services
from ..realizations.domain import CourseRealization
from ..realizations.services import RealizationService
from ..semester import services as semester_services
from ..semester.domain import Semester
from ..semester.services import SemesterService
from ..week_themes import services as week_theme_services
from ..week_themes.domain import WeekTheme
from ..week_themes.services import WeekThemeService


class SemesterDict(TypedDict):
    id: int
    year: int
    term: str
    start: str
    end: str


class CourseDict(TypedDict):
    id: int
    name: str
    description: str
    ects_credits: int


class RealizationDict(TypedDict):
    id: int
    course_id: int
    semester_id: int
    group: str


class LessonDict(TypedDict):
    id: int
    course_realization_id: int
    date: str
    start_time: str
    end_time: str
    topic: str
    notes: str


class HolidayDict(TypedDict):
    id: int
    date: str
    title: str


class NoTeachWeekDict(TypedDict):
    id: int
    semester_id: int
    week_number: int
    week_start: str
    title: str


class WeekThemeDict(TypedDict):
    id: int
    course_realization_id: int
    week_start: str
    title: str


class DeadlineDict(TypedDict):
    id: int
    course_realization_id: int
    date: str
    title: str


class DeletedDict(TypedDict):
    deleted: int


class McpError(Exception):
    """One adapted failure: a feature service's validation or lookup error, or a malformed input string."""


class McpWriteGuard:
    """The constant-time check of a presented bearer token against the configured `AIKANA_MCP_TOKEN`.

    Fails closed: with no configured token, or no token presented, every write is rejected.
    """

    def __init__(self, token: str) -> None:
        self._token = token

    def allows(self, presented: str | None) -> bool:
        if not self._token or presented is None:
            return False
        return hmac.compare_digest(presented, self._token)


# Every anticipated failure a feature service can raise, mapped to @McpError by @_translated.
_DOMAIN_ERRORS: tuple[type[Exception], ...] = (
    course_services.InvalidCourseError,
    course_services.DuplicateCourseError,
    course_services.UnknownCourseError,
    deadline_services.InvalidDeadlineError,
    deadline_services.UnknownDeadlineError,
    deadline_services.UnknownRealizationError,
    holiday_services.DuplicateHolidayError,
    holiday_services.InvalidHolidayError,
    holiday_services.UnknownHolidayError,
    lesson_services.InvalidLessonError,
    lesson_services.UnknownLessonError,
    lesson_services.UnknownRealizationError,
    no_teach_week_services.DuplicateNoTeachWeekError,
    no_teach_week_services.InvalidNoTeachWeekError,
    no_teach_week_services.UnknownNoTeachWeekError,
    no_teach_week_services.UnknownSemesterError,
    realization_services.InvalidRealizationError,
    realization_services.UnknownCourseError,
    realization_services.UnknownRealizationError,
    realization_services.UnknownSemesterError,
    semester_services.DuplicateSemesterError,
    semester_services.InvalidTermError,
    semester_services.UnknownSemesterError,
    week_theme_services.DuplicateWeekThemeError,
    week_theme_services.InvalidWeekThemeError,
    week_theme_services.UnknownWeekThemeError,
    week_theme_services.UnknownRealizationError,
)


@contextmanager
def _translated() -> Iterator[None]:
    """Re-raise a feature service's validation or lookup failure as the package-local @McpError."""
    try:
        yield
    except _DOMAIN_ERRORS as exc:
        raise McpError(str(exc)) from exc


def _parse_date(raw: str) -> date:
    """The date an ISO `yyyy-mm-dd` wire string carries, per ./mcp_server.sdd's wire format."""
    try:
        return date.fromisoformat(raw)
    except (TypeError, ValueError) as exc:
        raise McpError(f"Invalid date {raw!r}; expected ISO format `yyyy-mm-dd`.") from exc


def _parse_time(raw: str) -> time:
    """The time an ISO `HH:MM` wire string carries, per ./mcp_server.sdd's wire format."""
    try:
        return time.fromisoformat(raw)
    except (TypeError, ValueError) as exc:
        raise McpError(f"Invalid time {raw!r}; expected ISO format `HH:MM`.") from exc


def _course_dict(course: Course) -> CourseDict:
    return {
        "id": course.id,
        "name": course.name,
        "description": course.description,
        "ects_credits": course.ects_credits,
    }


def _realization_dict(realization: CourseRealization) -> RealizationDict:
    return {
        "id": realization.id,
        "course_id": realization.course_id,
        "semester_id": realization.semester_id,
        "group": realization.group,
    }


def _lesson_dict(lesson: Lesson) -> LessonDict:
    return {
        "id": lesson.id,
        "course_realization_id": lesson.course_realization_id,
        "date": lesson.date.isoformat(),
        "start_time": lesson.start_time.strftime("%H:%M"),
        "end_time": lesson.end_time.strftime("%H:%M"),
        "topic": lesson.topic,
        "notes": lesson.notes,
    }


def _holiday_dict(holiday: Holiday) -> HolidayDict:
    return {"id": holiday.id, "date": holiday.date.isoformat(), "title": holiday.title}


def _no_teach_week_dict(week: NoTeachWeek) -> NoTeachWeekDict:
    return {
        "id": week.id,
        "semester_id": week.semester_id,
        "week_number": week.week_number,
        "week_start": week.week_start.isoformat(),
        "title": week.title,
    }


def _week_theme_dict(theme: WeekTheme) -> WeekThemeDict:
    return {
        "id": theme.id,
        "course_realization_id": theme.course_realization_id,
        "week_start": theme.week_start.isoformat(),
        "title": theme.title,
    }


def _deadline_dict(deadline: Deadline) -> DeadlineDict:
    return {
        "id": deadline.id,
        "course_realization_id": deadline.course_realization_id,
        "date": deadline.date.isoformat(),
        "title": deadline.title,
    }


class McpService:
    """The eight feature services adapted to the plain-dict, ISO-string interface the MCP tools expose."""

    def __init__(
        self,
        course_service: CourseService,
        semester_service: SemesterService,
        realization_service: RealizationService,
        lesson_service: LessonService,
        holiday_service: HolidayService,
        no_teach_week_service: NoTeachWeekService,
        week_theme_service: WeekThemeService,
        deadline_service: DeadlineService,
    ) -> None:
        self.courses = course_service
        self.semesters = semester_service
        self.realizations = realization_service
        self.lessons = lesson_service
        self.holidays = holiday_service
        self.no_teach_weeks = no_teach_week_service
        self.week_themes = week_theme_service
        self.deadlines = deadline_service

    def _semester_dict(self, semester: Semester) -> SemesterDict:
        start, end = self.semesters.semester_bounds(semester)
        return {
            "id": semester.id,
            "year": semester.year,
            "term": semester.term,
            "start": start.isoformat(),
            "end": end.isoformat(),
        }

    # Semesters

    def list_semesters(self) -> list[SemesterDict]:
        return [self._semester_dict(semester) for semester in self.semesters.list_semesters()]

    def create_semester(self, year: int, term: str) -> SemesterDict:
        with _translated():
            semester = self.semesters.create_semester(year, term)
        return self._semester_dict(semester)

    def delete_semester(self, semester_id: int) -> DeletedDict:
        with _translated():
            self.semesters.delete_semester(semester_id)
        return {"deleted": semester_id}

    # Courses

    def list_courses(self) -> list[CourseDict]:
        return [_course_dict(course) for course in self.courses.list_courses()]

    def get_course(self, course_id: int) -> CourseDict:
        course = self.courses.get_course(course_id)
        if course is None:
            raise McpError(f"No Course with id {course_id!r}.")
        return _course_dict(course)

    def create_course(self, name: str, description: str, ects_credits: int) -> CourseDict:
        with _translated():
            course = self.courses.add_course(name, description, ects_credits)
        return _course_dict(course)

    def update_course(self, course_id: int, name: str, description: str, ects_credits: int) -> CourseDict:
        with _translated():
            course = self.courses.update_course(course_id, name, description, ects_credits)
        return _course_dict(course)

    def delete_course(self, course_id: int) -> DeletedDict:
        with _translated():
            self.courses.delete_course(course_id)
        return {"deleted": course_id}

    # CourseRealizations

    def get_realization(self, realization_id: int) -> RealizationDict:
        realization = self.realizations.get_realization(realization_id)
        if realization is None:
            raise McpError(f"No CourseRealization with id {realization_id!r}.")
        return _realization_dict(realization)

    def list_realizations(self, course_id: int | None = None, semester_id: int | None = None) -> list[RealizationDict]:
        if course_id is not None:
            return [_realization_dict(r) for r in self.realizations.list_realizations_for_course(course_id)]
        if semester_id is not None:
            return [_realization_dict(r) for r in self.realizations.list_realizations_for_semester(semester_id)]
        return [
            _realization_dict(r)
            for semester in self.semesters.list_semesters()
            for r in self.realizations.list_realizations_for_semester(semester.id)
        ]

    def create_realization(self, course_id: int, semester_id: int, group: str) -> RealizationDict:
        with _translated():
            realization = self.realizations.add_realization(course_id, semester_id, group)
        return _realization_dict(realization)

    def update_realization(self, realization_id: int, semester_id: int, group: str) -> RealizationDict:
        with _translated():
            realization = self.realizations.update_realization(realization_id, semester_id, group)
        return _realization_dict(realization)

    def delete_realization(self, realization_id: int) -> DeletedDict:
        with _translated():
            self.realizations.delete_realization(realization_id)
        return {"deleted": realization_id}

    # Lessons

    def get_lesson(self, lesson_id: int) -> LessonDict:
        lesson = self.lessons.get_lesson(lesson_id)
        if lesson is None:
            raise McpError(f"No Lesson with id {lesson_id!r}.")
        return _lesson_dict(lesson)

    def list_lessons(self, course_realization_id: int) -> list[LessonDict]:
        return [_lesson_dict(l) for l in self.lessons.list_lessons_for_realization(course_realization_id)]

    def list_lessons_for_range(self, start: str, end: str) -> list[LessonDict]:
        return [
            _lesson_dict(l)
            for l in self.lessons.list_lessons_for_range(_parse_date(start), _parse_date(end))
        ]

    def create_lesson(
        self,
        course_realization_id: int,
        lesson_date: str,
        start_time: str,
        end_time: str,
        topic: str,
        notes: str = "",
    ) -> LessonDict:
        with _translated():
            lesson = self.lessons.add_lesson(
                course_realization_id,
                _parse_date(lesson_date),
                _parse_time(start_time),
                _parse_time(end_time),
                topic,
                notes,
            )
        return _lesson_dict(lesson)

    def update_lesson(
        self, lesson_id: int, lesson_date: str, start_time: str, end_time: str, topic: str, notes: str = ""
    ) -> LessonDict:
        with _translated():
            lesson = self.lessons.update_lesson(
                lesson_id, _parse_date(lesson_date), _parse_time(start_time), _parse_time(end_time), topic, notes
            )
        return _lesson_dict(lesson)

    def delete_lesson(self, lesson_id: int) -> DeletedDict:
        with _translated():
            self.lessons.delete_lesson(lesson_id)
        return {"deleted": lesson_id}

    # Holidays

    def list_holidays(self, start: str, end: str) -> list[HolidayDict]:
        return [
            _holiday_dict(h)
            for h in self.holidays.list_holidays_for_range(_parse_date(start), _parse_date(end))
        ]

    def create_holiday(self, holiday_date: str, title: str) -> HolidayDict:
        with _translated():
            holiday = self.holidays.add_holiday(_parse_date(holiday_date), title)
        return _holiday_dict(holiday)

    def update_holiday(self, holiday_id: int, holiday_date: str, title: str) -> HolidayDict:
        with _translated():
            holiday = self.holidays.update_holiday(holiday_id, _parse_date(holiday_date), title)
        return _holiday_dict(holiday)

    def delete_holiday(self, holiday_id: int) -> DeletedDict:
        with _translated():
            self.holidays.delete_holiday(holiday_id)
        return {"deleted": holiday_id}

    # NoTeachWeeks

    def list_no_teach_weeks(self, semester_id: int) -> list[NoTeachWeekDict]:
        return [_no_teach_week_dict(w) for w in self.no_teach_weeks.list_no_teach_weeks(semester_id)]

    def create_no_teach_week(self, semester_id: int, week_number: int, title: str = "") -> NoTeachWeekDict:
        with _translated():
            week = self.no_teach_weeks.add_no_teach_week(
                semester_id, week_number, title or self.no_teach_weeks.default_title
            )
        return _no_teach_week_dict(week)

    def update_no_teach_week(self, no_teach_week_id: int, week_number: int, title: str) -> NoTeachWeekDict:
        with _translated():
            week = self.no_teach_weeks.update_no_teach_week(no_teach_week_id, week_number, title)
        return _no_teach_week_dict(week)

    def delete_no_teach_week(self, no_teach_week_id: int) -> DeletedDict:
        with _translated():
            self.no_teach_weeks.delete_no_teach_week(no_teach_week_id)
        return {"deleted": no_teach_week_id}

    # WeekThemes

    def get_week_theme(self, week_theme_id: int) -> WeekThemeDict:
        theme = self.week_themes.get_week_theme(week_theme_id)
        if theme is None:
            raise McpError(f"No WeekTheme with id {week_theme_id!r}.")
        return _week_theme_dict(theme)

    def list_week_themes(self, course_realization_id: int) -> list[WeekThemeDict]:
        return [_week_theme_dict(t) for t in self.week_themes.list_week_themes(course_realization_id)]

    def create_week_theme(self, course_realization_id: int, week_start: str, title: str) -> WeekThemeDict:
        with _translated():
            theme = self.week_themes.add_week_theme(
                course_realization_id, _parse_date(week_start), title
            )
        return _week_theme_dict(theme)

    def update_week_theme(self, week_theme_id: int, week_start: str, title: str) -> WeekThemeDict:
        with _translated():
            theme = self.week_themes.update_week_theme(week_theme_id, _parse_date(week_start), title)
        return _week_theme_dict(theme)

    def delete_week_theme(self, week_theme_id: int) -> DeletedDict:
        with _translated():
            self.week_themes.delete_week_theme(week_theme_id)
        return {"deleted": week_theme_id}

    # Deadlines

    def get_deadline(self, deadline_id: int) -> DeadlineDict:
        deadline = self.deadlines.get_deadline(deadline_id)
        if deadline is None:
            raise McpError(f"No Deadline with id {deadline_id!r}.")
        return _deadline_dict(deadline)

    def list_deadlines(self, course_realization_id: int) -> list[DeadlineDict]:
        return [
            _deadline_dict(d) for d in self.deadlines.list_deadlines_for_realization(course_realization_id)
        ]

    def list_deadlines_for_range(self, start: str, end: str) -> list[DeadlineDict]:
        return [
            _deadline_dict(d)
            for d in self.deadlines.list_deadlines_for_range(_parse_date(start), _parse_date(end))
        ]

    def create_deadline(self, course_realization_id: int, deadline_date: str, title: str) -> DeadlineDict:
        with _translated():
            deadline = self.deadlines.add_deadline(
                course_realization_id, _parse_date(deadline_date), title
            )
        return _deadline_dict(deadline)

    def update_deadline(self, deadline_id: int, deadline_date: str, title: str) -> DeadlineDict:
        with _translated():
            deadline = self.deadlines.update_deadline(deadline_id, _parse_date(deadline_date), title)
        return _deadline_dict(deadline)

    def delete_deadline(self, deadline_id: int) -> DeletedDict:
        with _translated():
            self.deadlines.delete_deadline(deadline_id)
        return {"deleted": deadline_id}
