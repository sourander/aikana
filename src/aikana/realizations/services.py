"""@CourseRealizationRepository-backed use cases and weekly view-model, per ./realizations.sdd."""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING

from ..courses.domain import Course
from ..courses.services import CourseService
from ..holidays.services import HolidayService
from ..lessons.services import LessonService
from ..no_teach_weeks.services import NoTeachWeekService
from .domain import CourseRealization
from .ports import CourseRealizationRepository

if TYPE_CHECKING:
    from ..semester.domain import Semester
    from ..semester.services import SemesterService


class UnknownCourseError(Exception):
    pass


class UnknownSemesterError(Exception):
    pass


class InvalidRealizationError(Exception):
    pass


class RealizationService:
    def __init__(
        self,
        repo: CourseRealizationRepository,
        course_service: CourseService,
        lesson_service: LessonService,
        holiday_service: HolidayService,
        no_teach_week_service: NoTeachWeekService,
    ) -> None:
        self.repo = repo
        self.course_service = course_service
        self.lesson_service = lesson_service
        self.holiday_service = holiday_service
        self.no_teach_week_service = no_teach_week_service
        # Set by main.py once ../semester/semester.sdd's SemesterService is constructed (mutual pair, wired in
        # two phases per ../architecture.sdd).
        self.semester_service: "SemesterService | None" = None

    def _semesters(self) -> "SemesterService":
        """The wired SemesterService; fails fast when main.py's two-phase wiring has not run."""
        if self.semester_service is None:
            raise RuntimeError("RealizationService.semester_service was not wired by the composition root.")
        return self.semester_service

    def list_realizations_for_semester(self, semester_id: str) -> list[CourseRealization]:
        return self.repo.list_for_semester(semester_id)

    def get_realization(self, realization_id: str) -> CourseRealization | None:
        return self.repo.get(realization_id) if realization_id else None

    def add_realization(self, course_id: str, semester_id: str, group: str) -> CourseRealization:
        if self.course_service.get_course(course_id) is None:
            raise UnknownCourseError(f"No Course with id {course_id!r}.")
        if self._semesters().get_semester(semester_id) is None:
            raise UnknownSemesterError(f"No Semester with id {semester_id!r}.")
        group = group.strip()
        if not group:
            raise InvalidRealizationError("A CourseRealization needs a non-empty group label.")
        return self.repo.add(course_id, semester_id, group)

    def realization_label(self, realization: CourseRealization, course: Course, semester: "Semester") -> str:
        """Composed at render time, never stored, per ./realizations.sdd Must."""
        return f"{course.name} ({realization.group}) \u2013 {semester.term.capitalize()} {semester.year}"

    def list_realization_options(self, semester_id: str) -> list[tuple[str, str]]:
        """(id, label) pairs for the realizations of one Semester, for the weekly view's dropdown."""
        semester = self._semesters().get_semester(semester_id)
        if semester is None:
            return []
        courses_by_id = {course.id: course for course in self.course_service.list_courses()}
        return [
            (r.id, self.realization_label(r, courses_by_id[r.course_id], semester))
            for r in self.list_realizations_for_semester(semester_id)
        ]

    def build_realization_view_model(
        self, realization_id: str, today: date | None = None
    ) -> "RealizationViewModel | None":
        realization = self.get_realization(realization_id)
        if realization is None:
            return None
        today = today or date.today()

        course = self.course_service.get_course(realization.course_id)
        semester = self._semesters().get_semester(realization.semester_id)
        start, end = self._semesters().semester_bounds(semester)

        lessons_by_day: dict[date, list] = {}
        for lesson in self.lesson_service.list_lessons_for_realization(realization.id):
            lessons_by_day.setdefault(lesson.date, []).append(lesson)
        holiday_titles_by_day = {
            holiday.date: holiday.title
            for holiday in self.holiday_service.list_holidays_for_range(start, end)
        }
        no_teach_titles_by_week = {
            week.week_number: week.title
            for week in self.no_teach_week_service.list_no_teach_weeks(realization.semester_id)
        }

        weeks: list[WeekRow] = []
        week_start = start - timedelta(days=start.weekday())
        while week_start <= end:
            week_end = week_start + timedelta(days=6)
            entries: list[WeekEntry] = []
            week_number = week_start.isocalendar()[1]
            no_teach_title = no_teach_titles_by_week.get(week_number)
            day = week_start
            if no_teach_title is not None:
                # A NoTeachWeek consumes its whole week, so no Lesson sub-row is shown for it, per
                # ../no_teach_weeks/no_teach_weeks.sdd.
                entries.append(
                    WeekEntry(
                        is_holiday=False,
                        is_no_teach_week=True,
                        time_range="",
                        title=no_teach_title,
                        notes="",
                    )
                )
            else:
                while day <= week_end:
                    for lesson in lessons_by_day.get(day, []):
                        entries.append(
                            WeekEntry(
                                is_holiday=False,
                                is_no_teach_week=False,
                                time_range=f"{lesson.start_time.strftime('%H:%M')}\u2013{lesson.end_time.strftime('%H:%M')}",
                                title=lesson.topic,
                                notes=lesson.notes,
                            )
                        )
                    holiday_title = holiday_titles_by_day.get(day)
                    if holiday_title:
                        entries.append(
                            WeekEntry(
                                is_holiday=True,
                                is_no_teach_week=False,
                                time_range="",
                                title=holiday_title,
                                notes="",
                            )
                        )
                    day += timedelta(days=1)
            weeks.append(
                WeekRow(
                    week_number=week_number,
                    start=week_start,
                    end=week_end,
                    entries=entries,
                    is_current_week=week_start <= today <= week_end,
                )
            )
            week_start += timedelta(days=7)

        return RealizationViewModel(
            realization=realization,
            label=self.realization_label(realization, course, semester),
            weeks=weeks,
        )


@dataclass(frozen=True)
class WeekEntry:
    """One Lesson or Holiday shown in a WeekRow's Lessons/Notes sub-rows."""

    is_holiday: bool
    is_no_teach_week: bool
    time_range: str
    title: str
    notes: str


@dataclass(frozen=True)
class WeekRow:
    week_number: int
    start: date
    end: date
    entries: list[WeekEntry]
    is_current_week: bool = False


@dataclass(frozen=True)
class RealizationViewModel:
    realization: CourseRealization
    label: str
    weeks: list[WeekRow]


