"""Registers the admin day dialog's routes, the package's only inbound adapter."""

from datetime import date, time, timedelta

from fasthtml.common import FtResponse, RedirectResponse

from ..auth.services import AuthService
from ..holidays.services import DuplicateHolidayError, HolidayService, InvalidHolidayError, UnknownHolidayError
from ..lessons.services import InvalidLessonError, LessonService, UnknownRealizationError
from ..no_teach_weeks.services import (
    DuplicateNoTeachWeekError,
    InvalidNoTeachWeekError,
    NoTeachWeekService,
    UnknownNoTeachWeekError,
    UnknownSemesterError,
)
from ..realizations import view as realizations_view
from ..realizations.services import RealizationService
from ..semester import view as semester_view
from ..semester.services import SemesterService
from ..shared import dates
from ..shared.ids import parse_id
from . import view

_ERROR_HEADERS = {"HX-Retarget": f"#{view.CONTAINER_ID}", "HX-Reswap": "innerHTML"}


def register_routes(
    app,
    semester_service: SemesterService,
    holiday_service: HolidayService,
    no_teach_week_service: NoTeachWeekService,
    lesson_service: LessonService,
    realization_service: RealizationService,
    auth_service: AuthService,
) -> None:
    def grid(semester_id: int | None):
        """The bare wall planner grid that a successful write swaps in, never the dialog container."""
        semester = semester_service.get_semester(semester_id)
        if semester is None:
            return ""
        return semester_view.semester_grid(semester_service.build_semester_view_model(semester), is_admin=True)

    def write_response(semester_id: int | None, realization_id: int | None):
        """The bare containing view a successful write swaps in: the weekly table or the wall planner grid."""
        if realization_id is not None:
            view_model = realization_service.build_realization_view_model(realization_id)
            if view_model is None:
                return ""
            return realizations_view.week_table(view_model, is_admin=True)
        return grid(semester_id)

    def holiday_on(day: date):
        """The Holiday already stored on that date, if any; a date carries at most one, per
        ../holidays/holidays.sdd."""
        found = holiday_service.list_holidays_for_range(day, day)
        return found[0] if found else None

    def no_teach_week_on(semester_id: int | None, day: date):
        """The NoTeachWeek blocking that date, if any, identified by the Monday its week starts on.

        The clicked day's own Monday is used rather than its ISO week number, so a Saturday or Sunday resolves to the
        same week as the weekdays around it, and a week stored for another ISO year still matches.
        """
        if semester_id is None:
            return None
        monday = day - timedelta(days=day.weekday())
        return next(
            (week for week in no_teach_week_service.list_no_teach_weeks(semester_id) if week.week_start == monday),
            None,
        )

    def dialog(
        kind: str,
        semester_id: int | None,
        day: date,
        values: dict,
        error: str,
        realization_id: int | None = None,
    ):
        return view.day_dialog(
            kind=kind,
            day=day,
            semester_id=semester_id,
            realization_options=realization_service.list_realization_options(semester_id),
            default_no_teach_title=no_teach_week_service.default_title,
            values=values,
            error=error,
            realization_id=realization_id,
            holiday=holiday_on(day),
            no_teach_week=no_teach_week_on(semester_id, day),
        )

    def parsed_day(day_str: str) -> date:
        try:
            return date.fromisoformat(day_str)
        except ValueError:
            raise _Rejected("That day is not a valid date.") from None

    def reject(
        day_str: str,
        semester_id: int | None,
        kind: str,
        values: dict,
        error: str,
        realization_id: int | None = None,
    ):
        """Re-render the dialog in place with a validation message, leaving the entry unstored."""
        try:
            day = parsed_day(day_str)
        except _Rejected:
            day = dates.today()
        return FtResponse(
            dialog(kind, semester_id, day, values, error, realization_id),
            status_code=422,
            headers=_ERROR_HEADERS,
        )

    @app.get(view.DIALOG_PATH)
    def open_dialog(session, semester_id: str = "", day: str = "", kind: str = "lesson", realization_id: str = ""):
        if not auth_service.is_admin(session):
            return RedirectResponse("/login", status_code=303)
        semester_id_value = parse_id(semester_id)
        realization_id_value = parse_id(realization_id)
        try:
            return dialog(kind, semester_id_value, parsed_day(day), {}, "", realization_id_value)
        except _Rejected as exc:
            return FtResponse(
                dialog(kind, semester_id_value, dates.today(), {}, str(exc), realization_id_value),
                status_code=422,
                headers=_ERROR_HEADERS,
            )

    @app.post(f"{view.DIALOG_PATH}/holiday")
    def add_holiday(session, semester_id: str = "", day: str = "", title: str = "", realization_id: str = ""):
        if not auth_service.is_admin(session):
            return RedirectResponse("/login", status_code=303)
        semester_id_value = parse_id(semester_id)
        realization_id_value = parse_id(realization_id)
        values = {"title": title}
        try:
            holiday_service.add_holiday(parsed_day(day), title)
        except (_Rejected, InvalidHolidayError) as exc:
            return reject(day, semester_id_value, "holiday", values, str(exc), realization_id_value)
        return write_response(semester_id_value, realization_id_value)

    @app.post(f"{view.DIALOG_PATH}/no-teach-week")
    def add_no_teach_week(
        session,
        semester_id: str = "",
        day: str = "",
        week_number: str = "",
        title: str = "",
        realization_id: str = "",
    ):
        if not auth_service.is_admin(session):
            return RedirectResponse("/login", status_code=303)
        semester_id_value = parse_id(semester_id)
        realization_id_value = parse_id(realization_id)
        values = {"week_number": week_number, "title": title}
        try:
            parsed_day(day)
            no_teach_week_service.add_no_teach_week(
                semester_id_value,
                parsed_week(week_number),
                title or no_teach_week_service.default_title,
            )
        except (
            _Rejected,
            UnknownSemesterError,
            InvalidNoTeachWeekError,
            DuplicateNoTeachWeekError,
        ) as exc:
            return reject(day, semester_id_value, "no_teach_week", values, str(exc), realization_id_value)
        return write_response(semester_id_value, realization_id_value)

    @app.post(f"{view.DIALOG_PATH}/lesson")
    def add_lesson(
        session,
        semester_id: str = "",
        day: str = "",
        course_realization_id: str = "",
        start_time: str = "",
        end_time: str = "",
        topic: str = "",
        notes: str = "",
        realization_id: str = "",
    ):
        if not auth_service.is_admin(session):
            return RedirectResponse("/login", status_code=303)
        semester_id_value = parse_id(semester_id)
        realization_id_value = parse_id(realization_id)
        values = {
            "course_realization_id": parse_id(course_realization_id),
            "start_time": start_time,
            "end_time": end_time,
            "topic": topic,
            "notes": notes,
        }
        try:
            lesson_service.add_lesson(
                parse_id(course_realization_id),
                parsed_day(day),
                parsed_time(start_time, "start"),
                parsed_time(end_time, "end"),
                topic,
                notes,
            )
        except (_Rejected, UnknownRealizationError, InvalidLessonError) as exc:
            return reject(day, semester_id_value, "lesson", values, str(exc), realization_id_value)
        return write_response(semester_id_value, realization_id_value)

    @app.post(f"{view.HOLIDAY_PATH}/{{holiday_id}}")
    def update_holiday(
        session,
        holiday_id: str,
        semester_id: str = "",
        day: str = "",
        title: str = "",
        realization_id: str = "",
    ):
        """Edits the Holiday already stored on the clicked date, per ./day_dialog.sdd."""
        if not auth_service.is_admin(session):
            return RedirectResponse("/login", status_code=303)
        semester_id_value = parse_id(semester_id)
        realization_id_value = parse_id(realization_id)
        holiday_id_value = parse_id(holiday_id)
        values = {"holiday_id": holiday_id_value, "day": day, "title": title}
        try:
            holiday_service.update_holiday(holiday_id_value, parsed_day(day), title)
        except (_Rejected, UnknownHolidayError, InvalidHolidayError, DuplicateHolidayError) as exc:
            return reject(day, semester_id_value, "holiday", values, str(exc), realization_id_value)
        return write_response(semester_id_value, realization_id_value)

    @app.post(f"{view.HOLIDAY_PATH}/{{holiday_id}}/delete")
    def delete_holiday(
        session,
        holiday_id: str,
        semester_id: str = "",
        day: str = "",
        realization_id: str = "",
    ):
        if not auth_service.is_admin(session):
            return RedirectResponse("/login", status_code=303)
        semester_id_value = parse_id(semester_id)
        realization_id_value = parse_id(realization_id)
        try:
            holiday_service.delete_holiday(parse_id(holiday_id))
        except UnknownHolidayError as exc:
            return reject(day, semester_id_value, "holiday", {}, str(exc), realization_id_value)
        return write_response(semester_id_value, realization_id_value)

    @app.post(f"{view.NO_TEACH_WEEK_PATH}/{{no_teach_week_id}}")
    def update_no_teach_week(
        session,
        no_teach_week_id: str,
        semester_id: str = "",
        day: str = "",
        week_number: str = "",
        title: str = "",
        realization_id: str = "",
    ):
        """Edits the NoTeachWeek already blocking the clicked date, per ./day_dialog.sdd."""
        if not auth_service.is_admin(session):
            return RedirectResponse("/login", status_code=303)
        semester_id_value = parse_id(semester_id)
        realization_id_value = parse_id(realization_id)
        no_teach_week_id_value = parse_id(no_teach_week_id)
        values = {"no_teach_week_id": no_teach_week_id_value, "week_number": week_number, "title": title}
        try:
            parsed_day(day)
            no_teach_week_service.update_no_teach_week(
                no_teach_week_id_value,
                parsed_week(week_number),
                title or no_teach_week_service.default_title,
            )
        except (
            _Rejected,
            UnknownNoTeachWeekError,
            InvalidNoTeachWeekError,
            DuplicateNoTeachWeekError,
        ) as exc:
            return reject(day, semester_id_value, "no_teach_week", values, str(exc), realization_id_value)
        return write_response(semester_id_value, realization_id_value)

    @app.post(f"{view.NO_TEACH_WEEK_PATH}/{{no_teach_week_id}}/delete")
    def delete_no_teach_week(
        session,
        no_teach_week_id: str,
        semester_id: str = "",
        day: str = "",
        realization_id: str = "",
    ):
        if not auth_service.is_admin(session):
            return RedirectResponse("/login", status_code=303)
        semester_id_value = parse_id(semester_id)
        realization_id_value = parse_id(realization_id)
        try:
            no_teach_week_service.delete_no_teach_week(parse_id(no_teach_week_id))
        except UnknownNoTeachWeekError as exc:
            return reject(day, semester_id_value, "no_teach_week", {}, str(exc), realization_id_value)
        return write_response(semester_id_value, realization_id_value)


class _Rejected(Exception):
    """A malformed form field, reported back in the dialog instead of reaching the services."""


def parsed_week(week_number: str) -> int:
    try:
        return int(week_number)
    except ValueError:
        raise _Rejected("A NoTeachWeek needs a whole-numbered week.") from None


def parsed_time(raw: str, which: str) -> time:
    try:
        return time.fromisoformat(raw)
    except ValueError:
        raise _Rejected(f"Enter a valid {which} time as HH:MM.") from None
