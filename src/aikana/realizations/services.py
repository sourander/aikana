"""@CourseRealizationRepository-backed use cases and weekly view-model, per ./realizations.sdd."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import TYPE_CHECKING

from ..courses.domain import Course
from ..courses.services import CourseService
from ..conferences.services import ConferenceService
from ..deadlines.services import DeadlineService
from ..holidays.services import HolidayService
from ..lessons.services import LessonService
from ..no_teach_weeks.services import NoTeachWeekService
from ..shared import dates
from ..week_themes.services import WeekThemeService
from .domain import CourseRealization
from .ports import CourseRealizationRepository

if TYPE_CHECKING:
    from ..semester.domain import Semester
    from ..semester.services import SemesterService


class UnknownCourseError(Exception):
    pass


class UnknownSemesterError(Exception):
    pass


class UnknownRealizationError(Exception):
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
        week_theme_service: WeekThemeService,
        deadline_service: DeadlineService,
        conference_service: ConferenceService,
    ) -> None:
        self.repo = repo
        self.course_service = course_service
        self.lesson_service = lesson_service
        self.holiday_service = holiday_service
        self.no_teach_week_service = no_teach_week_service
        self.week_theme_service = week_theme_service
        # ../deadlines/deadlines.sdd's service, used only to list the realization's Deadlines for the `Deadline`
        # column of the weekly view.
        self.deadline_service = deadline_service
        # ../conferences/conferences.sdd's service, used only to list the Semesters Conferences for the week rows'
        # `Lessons` column, like its Holidays.
        self.conference_service = conference_service
        # Set by main.py once ../semester/semester.sdd's SemesterService is constructed (mutual pair, wired in
        # two phases per ../architecture.sdd).
        self.semester_service: "SemesterService | None" = None

    def _semesters(self) -> "SemesterService":
        """The wired SemesterService; fails fast when main.py's two-phase wiring has not run."""
        if self.semester_service is None:
            raise RuntimeError("RealizationService.semester_service was not wired by the composition root.")
        return self.semester_service

    def list_realizations_for_course(self, course_id: int) -> list[CourseRealization]:
        return self.repo.list_for_course(course_id)

    def list_realizations_for_semester(self, semester_id: int) -> list[CourseRealization]:
        return self.repo.list_for_semester(semester_id)

    def get_realization(self, realization_id: int | None) -> CourseRealization | None:
        return self.repo.get(realization_id) if realization_id is not None else None

    def add_realization(
        self, course_id: int | None, semester_id: int | None, group: str
    ) -> CourseRealization:
        if self.course_service.get_course(course_id) is None:
            raise UnknownCourseError(f"No Course with id {course_id!r}.")
        if self._semesters().get_semester(semester_id) is None:
            raise UnknownSemesterError(f"No Semester with id {semester_id!r}.")
        group = group.strip()
        if not group:
            raise InvalidRealizationError("A CourseRealization needs a non-empty group label.")
        return self.repo.add(course_id, semester_id, group)

    def update_realization(
        self, realization_id: int | None, semester_id: int | None, group: str
    ) -> CourseRealization:
        """Re-labels a realization; its Course stays the one it was created under, per ../courses/courses.sdd."""
        existing = self.get_realization(realization_id)
        if existing is None:
            raise UnknownRealizationError(f"No CourseRealization with id {realization_id!r}.")
        if self._semesters().get_semester(semester_id) is None:
            raise UnknownSemesterError(f"No Semester with id {semester_id!r}.")
        group = group.strip()
        if not group:
            raise InvalidRealizationError("A CourseRealization needs a non-empty group label.")
        return self.repo.update(existing.id, existing.course_id, semester_id, group)

    def delete_realization(self, realization_id: int | None) -> None:
        """Removes a realization; the database's foreign keys take its Lessons with it."""
        existing = self.get_realization(realization_id)
        if existing is None:
            raise UnknownRealizationError(f"No CourseRealization with id {realization_id!r}.")
        self.repo.delete(existing.id)

    def realization_label(self, realization: CourseRealization, course: Course, semester: "Semester") -> str:
        """Composed at render time, never stored, per ./realizations.sdd Must."""
        return f"{course.name} ({realization.group}) \u2013 {semester.term.capitalize()} {semester.year}"

    def list_realization_options(self, semester_id: int | None) -> list[tuple[int, str]]:
        """(id, label) pairs for the realizations of one Semester, for the weekly view's dropdown."""
        semester = self._semesters().get_semester(semester_id)
        if semester is None:
            return []
        courses_by_id = {course.id: course for course in self.course_service.list_courses()}
        return [
            (r.id, self.realization_label(r, courses_by_id[r.course_id], semester))
            for r in self.list_realizations_for_semester(semester.id)
        ]

    def build_realization_view_model(
        self, realization_id: int | None, today: date | None = None
    ) -> "RealizationViewModel | None":
        realization = self.get_realization(realization_id)
        if realization is None:
            return None
        today = today or dates.today()

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
        # A ../conferences/conferences.sdd Conference is laid out like a Holiday here, only in purple, since it does
        # not block teaching and the whole calendar shares it rather than the one realization.
        conference_titles_by_day = {
            conference.date: conference.title
            for conference in self.conference_service.list_conferences_for_range(start, end)
        }
        no_teach_titles_by_week = {
            week.week_number: week.title
            for week in self.no_teach_week_service.list_no_teach_weeks(realization.semester_id)
        }
        # One listing of the realization's ../week_themes/week_themes.sdd themes gives the view-model both the title
        # each week renders and the id its dialogs address the stored theme by.
        themes_by_week_start: dict[date, tuple[int, str]] = {
            theme.week_start: (theme.id, theme.title)
            for theme in self.week_theme_service.list_week_themes(realization.id)
        }
        # One listing of the realization's ../deadlines/deadlines.sdd Deadlines gives every week row's `Deadline` cell
        # its entries and the id each per-Deadline dialog addresses the stored Deadline by.
        deadlines_by_day: dict[date, list[DeadlineEntry]] = {}
        for deadline in self.deadline_service.list_deadlines_for_realization(realization.id):
            deadlines_by_day.setdefault(deadline.date, []).append(
                DeadlineEntry(id=deadline.id, date=deadline.date, title=deadline.title)
            )

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
                        is_conference=False,
                        is_no_teach_week=True,
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
                                is_conference=False,
                                is_no_teach_week=False,
                                title=lesson.topic,
                                notes=lesson.notes,
                                start_time=lesson.start_time.strftime("%H:%M"),
                                end_time=lesson.end_time.strftime("%H:%M"),
                                lesson_id=lesson.id,
                                entry_date=lesson.date,
                            )
                        )
                    holiday_title = holiday_titles_by_day.get(day)
                    if holiday_title:
                        entries.append(
                            WeekEntry(
                                is_holiday=True,
                                is_conference=False,
                                is_no_teach_week=False,
                                title=holiday_title,
                                notes="",
                                entry_date=day,
                            )
                        )
                    conference_title = conference_titles_by_day.get(day)
                    if conference_title:
                        entries.append(
                            WeekEntry(
                                is_holiday=False,
                                is_conference=True,
                                is_no_teach_week=False,
                                title=conference_title,
                                notes="",
                                entry_date=day,
                            )
                        )
                    day += timedelta(days=1)
            theme_id, theme = themes_by_week_start.get(week_start, (None, ""))
            weeks.append(
                WeekRow(
                    week_number=week_number,
                    start=week_start,
                    end=week_end,
                    entries=entries,
                    is_current_week=week_start <= today <= week_end,
                    theme=theme,
                    theme_id=theme_id,
                    deadlines=[
                        entry
                        for day in _week_days(week_start)
                        for entry in deadlines_by_day.get(day, [])
                    ],
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
    """One Lesson, Holiday or ../conferences/conferences.sdd Conference shown in a WeekRow's Lessons/Notes sub-rows.

    `lesson_id` is set only for a Lesson and is what ../realizations.sdd's admin controls address it by;
    `entry_date` is the day a Lesson, a Holiday or a Conference falls on, which its cell's own day line shows, and is
    `None` for a NoTeachWeek, which consumes a whole week. `start_time` and `end_time` are the formatted
    `HH:MM` values of a Lesson and are empty for a Holiday, a Conference or a NoTeachWeek, whose cell shows no time.
    """

    is_holiday: bool
    is_conference: bool
    is_no_teach_week: bool
    title: str
    notes: str
    start_time: str = ""
    end_time: str = ""
    lesson_id: int | None = None
    entry_date: date | None = None


@dataclass(frozen=True)
class DeadlineEntry:
    """One ../deadlines/deadlines.sdd Deadline shown in a WeekRow's Deadline cell.

    `id` is the stored Deadline's id, which that cell's per-Deadline edit and delete controls address it by.
    """

    id: int
    date: date
    title: str


@dataclass(frozen=True)
class WeekRow:
    week_number: int
    start: date
    end: date
    entries: list[WeekEntry]
    is_current_week: bool = False
    # The week's ../week_themes/week_themes.sdd theme: `theme` is what the Week cell renders and `theme_id` is the
    # stored theme's id, which the Week cell's admin dialogs address it by. Both are empty for an unthemed week.
    theme: str = ""
    theme_id: int | None = None
    # The week's ../deadlines/deadlines.sdd Deadlines, ordered by date, which its Deadline cell renders and whose ids
    # that cell's admin controls address them by.
    deadlines: list[DeadlineEntry] = field(default_factory=list)


def _week_days(week_start: date) -> list[date]:
    """One Monday-to-Sunday week as its seven dates, so a row's `Deadline` cell can find its own days."""
    return [week_start + timedelta(days=offset) for offset in range(7)]


@dataclass(frozen=True)
class RealizationViewModel:
    realization: CourseRealization
    label: str
    weeks: list[WeekRow]
