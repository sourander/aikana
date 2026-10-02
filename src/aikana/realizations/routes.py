"""Registers the per-CourseRealization weekly view at `/realizations`, the package's only inbound adapter."""

from urllib.parse import urlencode

from ..auth import view as auth_view
from ..auth.services import AuthService
from ..semester.services import SemesterService
from ..shared import layout
from . import view
from .services import RealizationService

_PATH = "/realizations"


def share_url(request, realization_id: str, semester_id: str) -> str:
    """The canonical absolute URL of one realization's weekly view, carrying both ids, per ./realizations.sdd."""
    query = urlencode({"realization_id": realization_id, "semester_id": semester_id})
    return f"{str(request.base_url).rstrip('/')}{_PATH}?{query}"


def register_routes(
    app, realization_service: RealizationService, semester_service: SemesterService, auth_service: AuthService
) -> None:
    @app.get(_PATH)
    def index(session, request, realization_id: str = "", semester_id: str = ""):
        is_admin = auth_service.is_admin(session)
        admin_link = auth_view.header_link(is_admin)
        if not semester_id and realization_id:
            realization = realization_service.get_realization(realization_id)
            if realization is not None:
                semester_id = realization.semester_id
        semester_options = semester_service.list_semester_options()
        active_semester = semester_service.get_semester(semester_id) or semester_service.get_default_semester()
        if active_semester is None:
            return layout.page(
                view.no_semester_state(),
                active_nav="realizations",
                semester_options=semester_options,
                admin_link=admin_link,
            )

        options = realization_service.list_realization_options(active_semester.id)

        selected_id = realization_id if any(option_id == realization_id for option_id, _ in options) else (
            options[0][0] if options else ""
        )

        if not selected_id:
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
                view_model, is_admin=is_admin, share_url=share_url(request, selected_id, active_semester.id)
            ),
            active_nav="realizations",
            semester_options=semester_options,
            selected_semester_id=active_semester.id,
            selector=selector,
            admin_link=admin_link,
        )

