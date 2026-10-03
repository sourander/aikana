"""Registers the courses page at `/courses`, its per-Course Realizations and their create route, the package's
only inbound adapter.
"""

from urllib.parse import quote

from fasthtml.common import RedirectResponse

from ..auth import view as auth_view
from ..auth.services import AuthService
from ..lessons.services import LessonService
from ..realizations import services as realization_services
from ..realizations.services import RealizationService
from ..semester.services import SemesterService
from ..shared import layout
from ..shared.ids import parse_id
from . import services, view
from .services import CourseService


def register_routes(
    app,
    course_service: CourseService,
    realization_service: RealizationService,
    semester_service: SemesterService,
    auth_service: AuthService,
    lesson_service: LessonService,
) -> None:
    def _realization_label(realization, semesters_by_id) -> str:
        semester = semesters_by_id.get(realization.semester_id)
        if semester is None:
            return realization.group
        return f"{realization.group} \u2013 {semester_service.semester_label(semester)}"

    def _realization_rows(course_id: int, semesters_by_id) -> list[tuple[int, str, str, int]]:
        """A Course's realizations as `(id, label, group, semester_id)` rows, plain data for ./view.py."""
        return [
            (
                realization.id,
                _realization_label(realization, semesters_by_id),
                realization.group,
                realization.semester_id,
            )
            for realization in realization_service.list_realizations_for_course(course_id)
        ]

    def _lesson_count(realization_id: int) -> int:
        return len(lesson_service.list_lessons_for_realization(realization_id))

    def _course_delete_counts(rows_by_course: dict[int, list[tuple[int, str, str, int]]]) -> dict[int, tuple[int, int]]:
        """How many realizations and Lessons each Course's delete removes with it, for the confirmation dialog."""
        return {
            course_id: (
                len(rows),
                sum(_lesson_count(row[0]) for row in rows),
            )
            for course_id, rows in rows_by_course.items()
        }

    @app.get("/courses")
    def index(session, error: str = "", semester_id: str = ""):
        courses = course_service.list_courses()
        is_admin = auth_service.is_admin(session)
        admin_link = auth_view.header_link(is_admin)
        selected_semester = (
            semester_service.get_semester(parse_id(semester_id)) or semester_service.get_default_semester()
        )
        semester_options = semester_service.list_semester_options()
        selected_semester_id = selected_semester.id if selected_semester else None

        if not courses:
            content = view.create_course_form(error=error) if is_admin else view.no_course_notice()
            return layout.page(
                content,
                active_nav="courses",
                semester_options=semester_options,
                selected_semester_id=selected_semester_id,
                admin_link=admin_link,
            )
        semesters_by_id = {semester.id: semester for semester in semester_service.list_semesters()}
        rows_by_course = {course.id: _realization_rows(course.id, semesters_by_id) for course in courses}
        return layout.page(
            view.courses_page(
                courses,
                is_admin=is_admin,
                error=error,
                realizations_by_course=rows_by_course,
                semester_options=semester_options,
                selected_semester_id=selected_semester_id,
                course_delete_counts=_course_delete_counts(rows_by_course) if is_admin else {},
                realization_lesson_counts=(
                    {row[0]: _lesson_count(row[0]) for rows in rows_by_course.values() for row in rows}
                    if is_admin
                    else {}
                ),
            ),
            active_nav="courses",
            semester_options=semester_options,
            selected_semester_id=selected_semester_id,
            admin_link=admin_link,
        )

    @app.get("/courses/new")
    def new_course_form(session, error: str = ""):
        if not auth_service.is_admin(session):
            return RedirectResponse("/login", status_code=303)
        return layout.page(
            view.create_course_form(error=error), active_nav="courses", admin_link=auth_view.header_link(True)
        )

    @app.post("/courses")
    def create_course(session, name: str = "", description: str = "", ects_credits: int = 0):
        if not auth_service.is_admin(session):
            return RedirectResponse("/login", status_code=303)
        try:
            course_service.add_course(name, description, ects_credits)
        except (services.InvalidCourseError, services.DuplicateCourseError) as exc:
            return RedirectResponse(f"/courses/new?error={quote(str(exc))}", status_code=303)
        return RedirectResponse("/courses", status_code=303)

    @app.post("/courses/{course_id}")
    def update_course(session, course_id: str, name: str = "", description: str = "", ects_credits: int = 0):
        if not auth_service.is_admin(session):
            return RedirectResponse("/login", status_code=303)
        try:
            course_service.update_course(parse_id(course_id), name, description, ects_credits)
        except (services.InvalidCourseError, services.DuplicateCourseError, services.UnknownCourseError) as exc:
            return RedirectResponse(f"/courses?error={quote(str(exc))}", status_code=303)
        return RedirectResponse("/courses", status_code=303)

    @app.post("/courses/{course_id}/delete")
    def delete_course(session, course_id: str):
        if not auth_service.is_admin(session):
            return RedirectResponse("/login", status_code=303)
        try:
            # The database's foreign keys take the Course's realizations and their Lessons with it.
            course_service.delete_course(parse_id(course_id))
        except services.UnknownCourseError as exc:
            return RedirectResponse(f"/courses?error={quote(str(exc))}", status_code=303)
        return RedirectResponse("/courses", status_code=303)

    @app.post("/courses/{course_id}/realizations")
    def create_realization(session, course_id: str, group: str = "", semester_id: str = ""):
        if not auth_service.is_admin(session):
            return RedirectResponse("/login", status_code=303)
        back = f"/courses?semester_id={semester_id}" if semester_id else "/courses"
        try:
            realization_service.add_realization(parse_id(course_id), parse_id(semester_id), group)
        except (
            realization_services.UnknownCourseError,
            realization_services.UnknownSemesterError,
            realization_services.InvalidRealizationError,
        ) as exc:
            return RedirectResponse(f"{back}&error={quote(str(exc))}", status_code=303)
        return RedirectResponse(back, status_code=303)

    @app.post("/courses/{course_id}/realizations/{realization_id}")
    def update_realization(session, course_id: str, realization_id: str, group: str = "", semester_id: str = ""):
        if not auth_service.is_admin(session):
            return RedirectResponse("/login", status_code=303)
        back = f"/courses?semester_id={semester_id}" if semester_id else "/courses"
        try:
            realization_service.update_realization(parse_id(realization_id), parse_id(semester_id), group)
        except (
            realization_services.UnknownRealizationError,
            realization_services.UnknownSemesterError,
            realization_services.InvalidRealizationError,
        ) as exc:
            return RedirectResponse(f"{back}&error={quote(str(exc))}", status_code=303)
        return RedirectResponse(back, status_code=303)

    @app.post("/courses/{course_id}/realizations/{realization_id}/delete")
    def delete_realization(session, course_id: str, realization_id: str):
        if not auth_service.is_admin(session):
            return RedirectResponse("/login", status_code=303)
        try:
            realization_service.delete_realization(parse_id(realization_id))
        except realization_services.UnknownRealizationError as exc:
            return RedirectResponse(f"/courses?error={quote(str(exc))}", status_code=303)
        return RedirectResponse("/courses", status_code=303)
