"""Builds the semester wall-planner view-model by aggregating the other feature packages' services, per
./semester.sdd.
"""

import calendar
from dataclasses import dataclass
from datetime import date, time
from typing import TYPE_CHECKING

from ..courses.services import CourseService
from ..holidays.services import HolidayService
from ..lessons.services import LessonService
from ..no_teach_weeks.services import NoTeachWeekService
from . import domain
from .domain import Semester, Term
from .ports import SemesterRepository

if TYPE_CHECKING:
    from ..realizations.services import RealizationService

PALETTE = [
    "#2563eb",  # blue
    "#16a34a",  # green
    "#d97706",  # amber
    "#db2777",  # pink
    "#7c3aed",  # violet
    "#0891b2",  # cyan
]


class DuplicateSemesterError(Exception):
    pass


class InvalidTermError(Exception):
    pass


@dataclass(frozen=True)
class LessonSquare:
    color: str
    realization_id: str
    realization_label: str
    start_time: time
    end_time: time
    topic: str
    notes: str


@dataclass(frozen=True)
class DayCell:
    day: date
    weekday_label: str
    squares: list[LessonSquare]
    holiday_title: str | None
    no_teach_title: str | None
    is_today: bool = False


@dataclass(frozen=True)
class MonthColumn:
    label: str
    days: list[DayCell]


@dataclass(frozen=True)
class SemesterViewModel:
    semester: domain.Semester
    months: list[MonthColumn]


class SemesterService:
    def __init__(
        self,
        repo: SemesterRepository,
        course_service: CourseService,
        holiday_service: HolidayService,
        lesson_service: LessonService,
        realization_service: "RealizationService",
        no_teach_week_service: NoTeachWeekService,
    ) -> None:
        self.repo = repo
        self.course_service = course_service
        self.holiday_service = holiday_service
        self.lesson_service = lesson_service
        self.realization_service = realization_service
        self.no_teach_week_service = no_teach_week_service

    def list_semesters(self) -> list[Semester]:
        return self.repo.list()

    def get_semester(self, semester_id: str) -> Semester | None:
        return self.repo.get(semester_id) if semester_id else None

    def get_default_semester(self, today: date | None = None) -> Semester | None:
        return domain.default_semester(self.repo.list(), today or date.today())

    def create_semester(self, year: int, term: Term) -> Semester:
        if term not in ("spring", "fall"):
            raise InvalidTermError(f"Term must be 'spring' or 'fall', got {term!r}.")
        if any(s.year == year and s.term == term for s in self.repo.list()):
            raise DuplicateSemesterError(f"A {term} {year} Semester already exists.")
        semester = self.repo.add(year, term)
        # A new Semester starts with its term's default NoTeachWeeks, per ./semester.sdd and
        # ../no_teach_weeks/no_teach_weeks.sdd.
        self.no_teach_week_service.create_defaults_for_semester(semester.id)
        return semester

    def semester_bounds(self, semester: Semester) -> tuple[date, date]:
        return domain.semester_bounds(semester)

    def semester_label(self, semester: Semester) -> str:
        return f"{semester.term.capitalize()} {semester.year}"

    def list_semester_options(self) -> list[tuple[str, str]]:
        return [(semester.id, self.semester_label(semester)) for semester in self.list_semesters()]

    def build_semester_view_model(self, semester: Semester, today: date | None = None) -> SemesterViewModel:
        today = today or date.today()
        courses_by_id = {course.id: course for course in self.course_service.list_courses()}
        realizations = self.realization_service.list_realizations_for_semester(semester.id)
        colors = {r.id: PALETTE[i % len(PALETTE)] for i, r in enumerate(realizations)}
        labels = {
            r.id: self.realization_service.realization_label(r, courses_by_id[r.course_id], semester)
            for r in realizations
        }

        squares_by_day: dict[date, list[LessonSquare]] = {}
        for realization in realizations:
            for lesson in self.lesson_service.list_lessons_for_realization(realization.id):
                squares_by_day.setdefault(lesson.date, []).append(
                    LessonSquare(
                        color=colors[realization.id],
                        realization_id=realization.id,
                        realization_label=labels[realization.id],
                        start_time=lesson.start_time,
                        end_time=lesson.end_time,
                        topic=lesson.topic,
                        notes=lesson.notes,
                    )
                )

        start, end = domain.semester_bounds(semester)
        holiday_titles_by_day = {
            holiday.date: holiday.title
            for holiday in self.holiday_service.list_holidays_for_range(start, end)
        }
        no_teach_titles_by_day = self.no_teach_week_service.titles_by_teaching_day(semester.id)

        months = []
        for year, month in domain.semester_months(semester):
            _, days_in_month = calendar.monthrange(year, month)
            days = []
            for day_number in range(1, days_in_month + 1):
                day = date(year, month, day_number)
                days.append(
                    DayCell(
                        day=day,
                        weekday_label=day.strftime("%a"),
                        squares=squares_by_day.get(day, []),
                        holiday_title=holiday_titles_by_day.get(day),
                        no_teach_title=no_teach_titles_by_day.get(day),
                        is_today=day == today,
                    )
                )
            months.append(MonthColumn(label=date(year, month, 1).strftime("%B %Y"), days=days))

        return SemesterViewModel(semester=semester, months=months)

