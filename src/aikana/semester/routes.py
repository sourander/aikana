"""Registers the semester wall-planner view at `/`, the package's only inbound adapter."""

from ..shared import layout
from . import services, view


def register_routes(app) -> None:
    @app.get("/")
    def index():
        semester = services.get_current_semester()
        view_model = services.build_semester_view_model(semester)
        return layout.page(view.semester_view(view_model))
