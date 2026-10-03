"""Registers the admin day dialog's routes, the package's only inbound adapter."""

from datetime import date, time

from fasthtml.common import FtResponse, RedirectResponse

from ..auth.services import AuthService
from ..holidays.services import HolidayService, InvalidHolidayError
from ..lessons.services import InvalidLessonError, LessonService, UnknownRealizationError
from ..no_teach_weeks.services import (
    DuplicateNoTeachWeekError,
    InvalidNoTeachWeekError,
    NoTeachWeekService,
    UnknownSemesterError,
)
from ..realizations import view as realizations_view
from ..realizations.services import RealizationService
from ..semester import view as semester_view
from ..semester.services import SemesterService
from ..shared import dates
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
    def grid(semester_id: str):
        """The bare wall planner grid that a successful write swaps in, never the dialog container."""
        semester = semester_service.get_semester(semester_id)
        if semester is None:
            return ""
        return semester_view.semester_grid(semester_service.build_semester_view_model(semester), is_admin=True)

    def write_response(semester_id: str, realization_id: str):
        """The bare containing view a successful write swaps in: the weekly table or the wall planner grid."""
        if realization_id:
            view_model = realization_service.build_realization_view_model(realization_id)
            if view_model is None:
                return ""
            return realizations_view.week_table(view_model, is_admin=True)
        return grid(semester_id)

    def dialog(
        kind: str, semester_id: str, day: date, values: dict, error: str, realization_id: str = ""
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
        )

    def parsed_day(day_str: str) -> date:
        try:
            return date.fromisoformat(day_str)
        except ValueError:
            raise _Rejected("That day is not a valid date.") from None

    def reject(day_str: str, semester_id: str, kind: str, values: dict, error: str, realization_id: str = ""):
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
        try:
            return dialog(kind, semester_id, parsed_day(day), {}, "", realization_id)
        except _Rejected as exc:
            return FtResponse(
                dialog(kind, semester_id, dates.today(), {}, str(exc), realization_id),
                status_code=422,
                headers=_ERROR_HEADERS,
            )

    @app.post(f"{view.DIALOG_PATH}/holiday")
    def add_holiday(session, semester_id: str = "", day: str = "", title: str = "", realization_id: str = ""):
        if not auth_service.is_admin(session):
            return RedirectResponse("/login", status_code=303)
        values = {"title": title}
        try:
            holiday_service.add_holiday(parsed_day(day), title)
        except (_Rejected, InvalidHolidayError) as exc:
            return reject(day, semester_id, "holiday", values, str(exc), realization_id)
        return write_response(semester_id, realization_id)

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
        values = {"week_number": week_number, "title": title}
        try:
            parsed_day(day)
            no_teach_week_service.add_no_teach_week(
                semester_id,
                parsed_week(week_number),
                title or no_teach_week_service.default_title,
            )
        except (
            _Rejected,
            UnknownSemesterError,
            InvalidNoTeachWeekError,
            DuplicateNoTeachWeekError,
        ) as exc:
            return reject(day, semester_id, "no_teach_week", values, str(exc), realization_id)
        return write_response(semester_id, realization_id)

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
        values = {
            "course_realization_id": course_realization_id,
            "start_time": start_time,
            "end_time": end_time,
            "topic": topic,
            "notes": notes,
        }
        try:
            lesson_service.add_lesson(
                course_realization_id,
                parsed_day(day),
                parsed_time(start_time, "start"),
                parsed_time(end_time, "end"),
                topic,
                notes,
            )
        except (_Rejected, UnknownRealizationError, InvalidLessonError) as exc:
            return reject(day, semester_id, "lesson", values, str(exc), realization_id)
        return write_response(semester_id, realization_id)


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
