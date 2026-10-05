"""Builds the semester wall-planner view-model by aggregating the other feature packages' services, per
./semester.sdd.
"""

import calendar
from dataclasses import dataclass
from datetime import date, time
from typing import TYPE_CHECKING

from ..courses.services import CourseService
from ..conferences.services import ConferenceService
from ..deadlines.services import DeadlineService
from ..holidays.services import HolidayService
from ..lessons.services import LessonService
from ..no_teach_weeks.services import NoTeachWeekService
from ..shared import dates
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
    "#65a30d",  # lime
    "#ea580c",  # orange
    "#4f46e5",  # indigo
    "#0d9488",  # teal
]


class DuplicateSemesterError(Exception):
    pass


class UnknownSemesterError(Exception):
    pass


class InvalidTermError(Exception):
    pass


@dataclass(frozen=True)
class LessonSquare:
    color: str
    realization_id: int
    realization_label: str
    start_time: time
    end_time: time
    topic: str
    notes: str


@dataclass(frozen=True)
class DeadlineCircle:
    """One ../deadlines/deadlines.sdd Deadline drawn as a circle on its day row.

    `color` is the CourseRealization's own wall-planner color, the one its Lesson squares share.
    """

    color: str
    realization_id: int
    realization_label: str
    title: str


@dataclass(frozen=True)
class LegendEntry:
    """One CourseRealization in the wall planner's legend bar, in that realization's own square color."""

    color: str
    realization_id: int
    label: str


@dataclass(frozen=True)
class DayCell:
    day: date
    weekday_label: str
    # The ISO week number, on the Monday that starts the week and `None` on every other row.
    week_number: int | None
    squares: list[LessonSquare]
    circles: list[DeadlineCircle]
    holiday_title: str | None
    no_teach_title: str | None
    # The ../conferences/conferences.sdd title of the one Conference on that day, when there is one. A Conference
    # coexists with a Holiday and a NoTeachWeek title, since it does not block teaching.
    conference_title: str | None = None
    is_today: bool = False


@dataclass(frozen=True)
class MonthColumn:
    label: str
    days: list[DayCell]


@dataclass(frozen=True)
class SemesterViewModel:
    semester: domain.Semester
    months: list[MonthColumn]
    legend: list[LegendEntry]


class SemesterService:
    def __init__(
        self,
        repo: SemesterRepository,
        course_service: CourseService,
        holiday_service: HolidayService,
        lesson_service: LessonService,
        realization_service: "RealizationService",
        no_teach_week_service: NoTeachWeekService,
        deadline_service: DeadlineService,
        conference_service: ConferenceService,
    ) -> None:
        self.repo = repo
        self.course_service = course_service
        self.holiday_service = holiday_service
        self.lesson_service = lesson_service
        self.realization_service = realization_service
        self.no_teach_week_service = no_teach_week_service
        # ../deadlines/deadlines.sdd's service, used only to read the Semesters Deadlines for the wall planner's
        # circles.
        self.deadline_service = deadline_service
        # ../conferences/conferences.sdd's service, used only to read the Semesters Conferences for the wall
        # planner's purple titles.
        self.conference_service = conference_service

    def list_semesters(self) -> list[Semester]:
        return self.repo.list()

    def get_semester(self, semester_id: int | None) -> Semester | None:
        return self.repo.get(semester_id) if semester_id is not None else None

    def get_default_semester(self, today: date | None = None) -> Semester | None:
        return domain.default_semester(self.repo.list(), today or dates.today())

    def create_semester(self, year: int, term: Term) -> Semester:
        if term not in ("spring", "fall"):
            raise InvalidTermError(f"Term must be 'spring' or 'fall', got {term!r}.")
        if any(s.year == year and s.term == term for s in self.repo.list()):
            raise DuplicateSemesterError(f"A {term} {year} Semester already exists.")
        semester = self.repo.add(year, term)
        # A new Semester starts with its term's default NoTeachWeeks, per ./semester.sdd and
        # ../no_teach_weeks/no_teach_weeks.sdd.
        self.no_teach_week_service.create_defaults_for_semester(semester.id)
        # ...and with the Finnish public holidays of its own period, per ../holidays/holidays.sdd. The two terms of a
        # year cover disjoint periods, so this never competes with another Semester's holidays.
        self.holiday_service.create_defaults_for_range(*domain.semester_bounds(semester))
        return semester

    def delete_semester(self, semester_id: int | None) -> None:
        """Removes one Semester; the database's foreign keys take its CourseRealizations, their Lessons and
        its NoTeachWeeks with it, per ./semester.sdd."""
        existing = self.get_semester(semester_id)
        if existing is None:
            raise UnknownSemesterError(f"No Semester with id {semester_id!r}.")
        self.repo.delete(existing.id)

    def semester_bounds(self, semester: Semester) -> tuple[date, date]:
        return domain.semester_bounds(semester)

    def semester_label(self, semester: Semester) -> str:
        return f"{semester.term.capitalize()} {semester.year}"

    def list_semester_options(self) -> list[tuple[int, str]]:
        return [(semester.id, self.semester_label(semester)) for semester in self.list_semesters()]

    def build_semester_view_model(self, semester: Semester, today: date | None = None) -> SemesterViewModel:
        today = today or dates.today()
        courses_by_id = {course.id: course for course in self.course_service.list_courses()}
        realizations = self.realization_service.list_realizations_for_semester(semester.id)
        colors = {r.id: PALETTE[i % len(PALETTE)] for i, r in enumerate(realizations)}
        labels = {
            r.id: self.realization_service.realization_label(r, courses_by_id[r.course_id], semester)
            for r in realizations
        }
        # The legend names every realization in the color its squares already use, in the same order, so a row's
        # marker and its legend entry always read together.
        legend = [
            LegendEntry(
                color=colors[r.id],
                realization_id=r.id,
                label=f"{courses_by_id[r.course_id].name} ({r.group})",
            )
            for r in realizations
        ]

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
        conference_titles_by_day = {
            conference.date: conference.title
            for conference in self.conference_service.list_conferences_for_range(start, end)
        }

        # Every Deadline of the Semester's own realizations, colored with the color its Lesson squares share, so a
        # deadline circle reads as that realization's marker.
        circles_by_day: dict[date, list[DeadlineCircle]] = {}
        for deadline in self.deadline_service.list_deadlines_for_range(start, end):
            realization_id = deadline.course_realization_id
            if realization_id not in colors:
                continue
            circles_by_day.setdefault(deadline.date, []).append(
                DeadlineCircle(
                    color=colors[realization_id],
                    realization_id=realization_id,
                    realization_label=labels[realization_id],
                    title=deadline.title,
                )
            )

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
                        # Only the Monday that starts a week carries that week's number, since a week spanning two
                        # month columns would otherwise repeat it.
                        week_number=day.isocalendar().week if day.weekday() == 0 else None,
                        squares=squares_by_day.get(day, []),
                        # A Deadline is an obligation rather than teaching, so its circle stays on a NoTeachWeek's
                        # rows, unlike the Lesson squares.
                        circles=circles_by_day.get(day, []),
                        holiday_title=holiday_titles_by_day.get(day),
                        no_teach_title=no_teach_titles_by_day.get(day),
                        conference_title=conference_titles_by_day.get(day),
                        is_today=day == today,
                    )
                )
            months.append(MonthColumn(label=date(year, month, 1).strftime("%B %Y"), days=days))

        return SemesterViewModel(semester=semester, months=months, legend=legend)

