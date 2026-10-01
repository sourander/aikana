"""@CourseRealizationRepository-backed use cases and weekly view-model, per ./realizations.sdd."""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING

from ..courses.domain import Course
from ..courses.services import CourseService
from ..holidays.services import HolidayService
from ..lessons.services import LessonService
from .domain import CourseRealization
from .ports import CourseRealizationRepository

if TYPE_CHECKING:
    from ..semester.domain import Semester
    from ..semester.services import SemesterService


class RealizationService:
    def __init__(
        self,
        repo: CourseRealizationRepository,
        course_service: CourseService,
        lesson_service: LessonService,
        holiday_service: HolidayService,
    ) -> None:
        self.repo = repo
        self.course_service = course_service
        self.lesson_service = lesson_service
        self.holiday_service = holiday_service
        # Set by main.py once ../semester/semester.sdd's SemesterService is constructed (mutual pair, wired in
        # two phases per ../architecture.sdd).
        self.semester_service: "SemesterService | None" = None

    def list_realizations_for_semester(self, semester_id: str) -> list[CourseRealization]:
        return self.repo.list_for_semester(semester_id)

    def get_realization(self, realization_id: str) -> CourseRealization | None:
        return self.repo.get(realization_id) if realization_id else None

    def add_realization(self, course_id: str, semester_id: str, group: str) -> CourseRealization:
        return self.repo.add(course_id, semester_id, group)

    def realization_label(self, realization: CourseRealization, course: Course, semester: "Semester") -> str:
        """Composed at render time, never stored, per ./realizations.sdd Must."""
        return f"{course.name} ({realization.group}) \u2013 {semester.term.capitalize()} {semester.year}"

    def list_realization_options(self, semester_id: str) -> list[tuple[str, str]]:
        """(id, label) pairs for the realizations of one Semester, for the weekly view's dropdown."""
        semester = self.semester_service.get_semester(semester_id)
        if semester is None:
            return []
        courses_by_id = {course.id: course for course in self.course_service.list_courses()}
        return [
            (r.id, self.realization_label(r, courses_by_id[r.course_id], semester))
            for r in self.list_realizations_for_semester(semester_id)
        ]

    def build_realization_view_model(self, realization_id: str) -> "RealizationViewModel | None":
        realization = self.get_realization(realization_id)
        if realization is None:
            return None

        course = self.course_service.get_course(realization.course_id)
        semester = self.semester_service.get_semester(realization.semester_id)
        start, end = self.semester_service.semester_bounds(semester)

        lessons_by_day: dict[date, list] = {}
        for lesson in self.lesson_service.list_lessons_for_realization(realization.id):
            lessons_by_day.setdefault(lesson.date, []).append(lesson)
        holiday_titles_by_day = {
            holiday.date: holiday.title
            for holiday in self.holiday_service.list_holidays_for_range(start, end)
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
            weeks.append(
                WeekRow(week_number=week_start.isocalendar()[1], start=week_start, end=week_end, entries=entries)
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


