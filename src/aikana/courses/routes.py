"""Registers the courses page at `/courses`, the package's only inbound adapter."""

from urllib.parse import quote

from fasthtml.common import RedirectResponse

from ..auth import view as auth_view
from ..auth.services import AuthService
from ..semester.services import SemesterService
from ..shared import layout
from . import services, view
from .services import CourseService


def register_routes(
    app, course_service: CourseService, semester_service: SemesterService, auth_service: AuthService
) -> None:
    @app.get("/courses")
    def index(session, error: str = "", semester_id: str = ""):
        courses = course_service.list_courses()
        is_admin = auth_service.is_admin(session)
        admin_link = auth_view.header_link(is_admin)
        selected_semester = semester_service.get_semester(semester_id) or semester_service.get_default_semester()
        semester_options = semester_service.list_semester_options()
        selected_semester_id = selected_semester.id if selected_semester else ""

        if not courses:
            content = view.create_course_form(error=error) if is_admin else view.no_course_notice()
            return layout.page(
                content,
                active_nav="courses",
                semester_options=semester_options,
                selected_semester_id=selected_semester_id,
                admin_link=admin_link,
            )
        return layout.page(
            view.courses_page(courses, is_admin=is_admin, error=error),
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
            course_service.update_course(course_id, name, description, ects_credits)
        except (services.InvalidCourseError, services.DuplicateCourseError, services.UnknownCourseError) as exc:
            return RedirectResponse(f"/courses?error={quote(str(exc))}", status_code=303)
        return RedirectResponse("/courses", status_code=303)
