"""Registers the semester wall-planner view at `/`, the package's only inbound adapter."""

from urllib.parse import quote

from fasthtml.common import Div, RedirectResponse

from ..auth import view as auth_view
from ..auth.services import AuthService
from ..shared import layout
from . import services, view
from .services import SemesterService


def register_routes(app, semester_service: SemesterService, auth_service: AuthService) -> None:
    @app.get("/")
    def index(session, semester_id: str = ""):
        semester = semester_service.get_semester(semester_id) or semester_service.get_default_semester()
        admin_link = auth_view.header_link(auth_service.is_admin(session))

        if semester is None:
            return layout.page(view.create_semester_form(), active_nav="semester", admin_link=admin_link)

        view_model = semester_service.build_semester_view_model(semester)
        selector = view.semester_selector(semester_service.list_semester_options(), semester.id)
        if auth_service.is_admin(session):
            selector = Div(selector, view.new_semester_control(), cls="flex items-center gap-3")
        return layout.page(
            view.semester_view(view_model), active_nav="semester", selector=selector, admin_link=admin_link
        )

    @app.get("/semesters/new")
    def new_semester_form(session, error: str = ""):
        if not auth_service.is_admin(session):
            return RedirectResponse("/login", status_code=303)
        admin_link = auth_view.header_link(True)
        return layout.page(view.create_semester_form(error=error), active_nav="semester", admin_link=admin_link)

    @app.post("/semesters")
    def create_semester(session, year: int = 0, term: str = "fall"):
        if not auth_service.is_admin(session):
            return RedirectResponse("/login", status_code=303)
        try:
            semester = semester_service.create_semester(year, term)
        except services.DuplicateSemesterError as exc:
            return RedirectResponse(f"/semesters/new?error={quote(str(exc))}", status_code=303)
        return RedirectResponse(f"/?semester_id={semester.id}", status_code=303)

