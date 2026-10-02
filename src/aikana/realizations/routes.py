"""Registers the per-CourseRealization weekly view at `/realizations`, the package's only inbound adapter."""

from ..auth import view as auth_view
from ..auth.services import AuthService
from ..semester.services import SemesterService
from ..shared import layout
from . import view
from .services import RealizationService


def register_routes(
    app, realization_service: RealizationService, semester_service: SemesterService, auth_service: AuthService
) -> None:
    @app.get("/realizations")
    def index(session, realization_id: str = ""):
        admin_link = auth_view.header_link(auth_service.is_admin(session))
        active_semester = semester_service.get_default_semester()
        if active_semester is None:
            return layout.page(view.no_semester_state(), active_nav="realizations", admin_link=admin_link)

        options = realization_service.list_realization_options(active_semester.id)

        selected_id = realization_id if any(option_id == realization_id for option_id, _ in options) else (
            options[0][0] if options else ""
        )

        if not selected_id:
            return layout.page(view.empty_state(), active_nav="realizations", admin_link=admin_link)

        view_model = realization_service.build_realization_view_model(selected_id)
        selector = view.realization_selector(options, selected_id)
        return layout.page(
            view.realization_view(view_model), active_nav="realizations", selector=selector, admin_link=admin_link
        )

