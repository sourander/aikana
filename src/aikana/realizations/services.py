"""Placeholder stand-in for a @CourseRealizationRepository-backed service, per ./realizations.sdd Tasks."""

from dataclasses import dataclass
from datetime import date, timedelta

from ..courses import services as courses_services
from ..courses.domain import Course
from ..holidays import services as holidays_services
from ..lessons import services as lessons_services
from ..semester import services as semester_services
from ..semester.domain import Semester
from .domain import CourseRealization

_PLACEHOLDER_REALIZATIONS = [
    CourseRealization(id="realization-1", course_id="course-1", semester_id="semester-1", group="TTV24SP"),
    CourseRealization(id="realization-2", course_id="course-2", semester_id="semester-1", group="TTV25A"),
]


def list_realizations_for_semester(semester_id: str) -> list[CourseRealization]:
    return [r for r in _PLACEHOLDER_REALIZATIONS if r.semester_id == semester_id]


def get_realization(realization_id: str) -> CourseRealization | None:
    return next((r for r in _PLACEHOLDER_REALIZATIONS if r.id == realization_id), None)


def realization_label(realization: CourseRealization, course: Course, semester: Semester) -> str:
    """Composed at render time, never stored, per ./realizations.sdd Must."""
    return f"{course.name} ({realization.group}) \u2013 {semester.term.capitalize()} {semester.year}"


def list_realization_options(semester_id: str) -> list[tuple[str, str]]:
    """(id, label) pairs for the realizations of one Semester, for the weekly view's dropdown."""
    semester = semester_services.get_semester(semester_id)
    courses_by_id = {course.id: course for course in courses_services.list_courses()}
    return [
        (r.id, realization_label(r, courses_by_id[r.course_id], semester))
        for r in list_realizations_for_semester(semester_id)
    ]


@dataclass(frozen=True)
class WeekEntry:
    """One Lesson or Holiday shown in a WeekRow's Lessons/Notes sub-rows."""

    is_holiday: bool
    time_range: str
    title: str
    notes: str


@dataclass(frozen=True)
class WeekRow:
    week_number: int
    start: date
    end: date
    entries: list[WeekEntry]


@dataclass(frozen=True)
class RealizationViewModel:
    realization: CourseRealization
    label: str
    weeks: list[WeekRow]


def build_realization_view_model(realization_id: str) -> RealizationViewModel | None:
    realization = get_realization(realization_id)
    if realization is None:
        return None

    course = courses_services.get_course(realization.course_id)
    semester = semester_services.get_semester(realization.semester_id)
    start, end = semester_services.semester_bounds(semester)

    lessons_by_day: dict[date, list] = {}
    for lesson in lessons_services.list_lessons_for_realization(realization.id):
        lessons_by_day.setdefault(lesson.date, []).append(lesson)
    holiday_titles_by_day = {
        holiday.date: holiday.title for holiday in holidays_services.list_holidays_for_range(start, end)
    }

    weeks: list[WeekRow] = []
    week_start = start - timedelta(days=start.weekday())
    while week_start <= end:
        week_end = week_start + timedelta(days=6)
        entries: list[WeekEntry] = []
        day = week_start
        while day <= week_end:
            for lesson in lessons_by_day.get(day, []):
                entries.append(
                    WeekEntry(
                        is_holiday=False,
                        time_range=f"{lesson.start_time.strftime('%H:%M')}\u2013{lesson.end_time.strftime('%H:%M')}",
                        title=lesson.topic,
                        notes=lesson.notes,
                    )
                )
            holiday_title = holiday_titles_by_day.get(day)
            if holiday_title:
                entries.append(WeekEntry(is_holiday=True, time_range="", title=holiday_title, notes=""))
            day += timedelta(days=1)
        weeks.append(WeekRow(week_number=week_start.isocalendar()[1], start=week_start, end=week_end, entries=entries))
        week_start += timedelta(days=7)

    return RealizationViewModel(
        realization=realization,
        label=realization_label(realization, course, semester),
        weeks=weeks,
    )

