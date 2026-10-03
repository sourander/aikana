"""Registers the per-CourseRealization weekly view at `/realizations`, its per-Lesson edit and delete routes, the
package's only inbound adapter.
"""

from datetime import date, time
from urllib.parse import quote, urlencode

from fasthtml.common import RedirectResponse

from ..auth import view as auth_view
from ..auth.services import AuthService
from ..lessons.services import InvalidLessonError, LessonService, UnknownLessonError
from ..semester.services import SemesterService
from ..shared import layout
from ..shared.ids import parse_id
from . import view
from .services import RealizationService

_PATH = "/realizations"
_LESSON_PATH = f"{_PATH}/lessons"


def share_url(request, realization_id: int, semester_id: int) -> str:
    """The canonical absolute URL of one realization's weekly view, carrying both ids, per ./realizations.sdd."""
    query = urlencode({"realization_id": realization_id, "semester_id": semester_id})
    return f"{str(request.base_url).rstrip('/')}{_PATH}?{query}"


def register_routes(
    app,
    realization_service: RealizationService,
    semester_service: SemesterService,
    auth_service: AuthService,
    lesson_service: LessonService,
) -> None:
    def lesson_back_url(lesson_id: int | None, error: str = "") -> str:
        """The weekly view of the CourseRealization the Lesson belongs to, so a write returns to it."""
        lesson = lesson_service.get_lesson(lesson_id)
        realization = realization_service.get_realization(lesson.course_realization_id) if lesson else None
        if realization is None:
            return f"{_PATH}?error={quote(error)}" if error else _PATH
        query = urlencode({"realization_id": realization.id, "semester_id": realization.semester_id})
        return f"{_PATH}?{query}" + (f"&error={quote(error)}" if error else "")

    @app.get(_PATH)
    def index(session, request, realization_id: str = "", semester_id: str = "", error: str = ""):
        is_admin = auth_service.is_admin(session)
        admin_link = auth_view.header_link(is_admin)
        realization_id_value = parse_id(realization_id)
        semester_id_value = parse_id(semester_id)
        if semester_id_value is None and realization_id_value is not None:
            realization = realization_service.get_realization(realization_id_value)
            if realization is not None:
                semester_id_value = realization.semester_id
        semester_options = semester_service.list_semester_options()
        active_semester = (
            semester_service.get_semester(semester_id_value) or semester_service.get_default_semester()
        )
        if active_semester is None:
            return layout.page(
                view.no_semester_state(),
                active_nav="realizations",
                semester_options=semester_options,
                admin_link=admin_link,
            )

        options = realization_service.list_realization_options(active_semester.id)

        selected_id = (
            realization_id_value
            if any(option_id == realization_id_value for option_id, _ in options)
            else (options[0][0] if options else None)
        )

        if selected_id is None:
            return layout.page(
                view.empty_state(),
                active_nav="realizations",
                semester_options=semester_options,
                selected_semester_id=active_semester.id,
                admin_link=admin_link,
            )

        view_model = realization_service.build_realization_view_model(selected_id)
        selector = view.realization_selector(options, selected_id)
        return layout.page(
            view.realization_view(
                view_model,
                is_admin=is_admin,
                share_url=share_url(request, selected_id, active_semester.id),
                error=error,
            ),
            active_nav="realizations",
            semester_options=semester_options,
            selected_semester_id=active_semester.id,
            selector=selector,
            admin_link=admin_link,
        )

    @app.post(f"{_LESSON_PATH}/{{lesson_id}}")
    def update_lesson(
        session,
        lesson_id: str,
        day: str = "",
        start_time: str = "",
        end_time: str = "",
        topic: str = "",
        notes: str = "",
    ):
        """Edits one Lesson in place, per ../lessons/lessons.sdd; a rejected write returns to the same week table."""
        if not auth_service.is_admin(session):
            return RedirectResponse("/login", status_code=303)
        lesson_id_value = parse_id(lesson_id)
        try:
            lesson_service.update_lesson(
                lesson_id_value,
                parsed_day(day),
                parsed_time(start_time, "start"),
                parsed_time(end_time, "end"),
                topic,
                notes,
            )
        except (_Rejected, UnknownLessonError, InvalidLessonError) as exc:
            return RedirectResponse(lesson_back_url(lesson_id_value, str(exc)), status_code=303)
        return RedirectResponse(lesson_back_url(lesson_id_value), status_code=303)

    @app.post(f"{_LESSON_PATH}/{{lesson_id}}/delete")
    def delete_lesson(session, lesson_id: str):
        if not auth_service.is_admin(session):
            return RedirectResponse("/login", status_code=303)
        lesson_id_value = parse_id(lesson_id)
        try:
            lesson_service.delete_lesson(lesson_id_value)
        except UnknownLessonError as exc:
            return RedirectResponse(lesson_back_url(lesson_id_value, str(exc)), status_code=303)
        return RedirectResponse(lesson_back_url(lesson_id_value), status_code=303)


class _Rejected(Exception):
    """A malformed form field, reported back on the weekly view instead of reaching the services."""


def parsed_day(day: str) -> date:
    try:
        return date.fromisoformat(day)
    except ValueError:
        raise _Rejected("Enter a valid date.") from None


def parsed_time(raw: str, which: str) -> time:
    try:
        return time.fromisoformat(raw)
    except ValueError:
        raise _Rejected(f"Enter a valid {which} time as HH:MM.") from None
