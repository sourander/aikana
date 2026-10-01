"""Builds the semester wall-planner view-model by aggregating the other feature packages' services.

The single hardcoded Semester stands in for a @SemesterRepository-backed lookup until persistence exists,
per ./semester.sdd Tasks.
"""

import calendar
from dataclasses import dataclass
from datetime import date, time

from ..courses import services as courses_services
from ..holidays import services as holidays_services
from ..lessons import services as lessons_services
from ..realizations import services as realizations_services
from . import domain

_SEMESTERS = {
    "semester-1": domain.Semester(id="semester-1", year=2026, term="fall"),
    "semester-2": domain.Semester(id="semester-2", year=2027, term="spring"),
}

PALETTE = [
    "#2563eb",  # blue
    "#16a34a",  # green
    "#d97706",  # amber
    "#db2777",  # pink
    "#7c3aed",  # violet
    "#0891b2",  # cyan
]


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


@dataclass(frozen=True)
class MonthColumn:
    label: str
    days: list[DayCell]


@dataclass(frozen=True)
class SemesterViewModel:
    semester: domain.Semester
    months: list[MonthColumn]


def list_semesters() -> list[domain.Semester]:
    return list(_SEMESTERS.values())


def get_semester(semester_id: str) -> domain.Semester | None:
    return _SEMESTERS.get(semester_id)


def get_default_semester(today: date | None = None) -> domain.Semester:
    return domain.default_semester(list(_SEMESTERS.values()), today or date.today())


def semester_bounds(semester: domain.Semester) -> tuple[date, date]:
    return domain.semester_bounds(semester)


def semester_label(semester: domain.Semester) -> str:
    return f"{semester.term.capitalize()} {semester.year}"


def list_semester_options() -> list[tuple[str, str]]:
    return [(semester.id, semester_label(semester)) for semester in list_semesters()]


def build_semester_view_model(semester: domain.Semester) -> SemesterViewModel:
    courses_by_id = {course.id: course for course in courses_services.list_courses()}
    realizations = realizations_services.list_realizations_for_semester(semester.id)
    colors = {r.id: PALETTE[i % len(PALETTE)] for i, r in enumerate(realizations)}
    labels = {
        r.id: realizations_services.realization_label(r, courses_by_id[r.course_id], semester) for r in realizations
    }

    squares_by_day: dict[date, list[LessonSquare]] = {}
    for realization in realizations:
        for lesson in lessons_services.list_lessons_for_realization(realization.id):
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
    holiday_titles_by_day = {holiday.date: holiday.title for holiday in holidays_services.list_holidays_for_range(start, end)}

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
                )
            )
        months.append(MonthColumn(label=date(year, month, 1).strftime("%B %Y"), days=days))

    return SemesterViewModel(semester=semester, months=months)
