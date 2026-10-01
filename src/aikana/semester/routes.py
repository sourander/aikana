"""Registers the semester wall-planner view at `/`, the package's only inbound adapter."""

from ..shared import layout
from . import services, view


def register_routes(app) -> None:
    @app.get("/")
    def index(semester_id: str = ""):
        semester = services.get_semester(semester_id) or services.get_default_semester()
        view_model = services.build_semester_view_model(semester)
        selector = view.semester_selector(services.list_semester_options(), semester.id)
        return layout.page(view.semester_view(view_model), active_nav="semester", selector=selector)
