"""Registers the per-CourseRealization weekly view at `/realizations`, the package's only inbound adapter."""

from ..semester import services as semester_services
from ..shared import layout
from . import services, view


def register_routes(app) -> None:
    @app.get("/realizations")
    def index(realization_id: str = ""):
        active_semester = semester_services.get_default_semester()
        options = services.list_realization_options(active_semester.id)

        selected_id = realization_id if any(option_id == realization_id for option_id, _ in options) else (
            options[0][0] if options else ""
        )

        if not selected_id:
            return layout.page(view.empty_state(), active_nav="realizations")

        view_model = services.build_realization_view_model(selected_id)
        selector = view.realization_selector(options, selected_id)
        return layout.page(view.realization_view(view_model), active_nav="realizations", selector=selector)
