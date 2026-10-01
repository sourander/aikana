"""Registers `/login` and `/logout`, the package's only inbound adapter."""

from fasthtml.common import RedirectResponse

from ..shared import layout
from . import services, view


def register_routes(app, auth_service: services.AuthService) -> None:
    @app.get("/login")
    def login_form(session, error: str = ""):
        if auth_service.is_admin(session):
            return RedirectResponse("/", status_code=303)
        return layout.page(view.login_form(error=bool(error)), active_nav="login")

    @app.post("/login")
    def login_submit(session, password: str = ""):
        if auth_service.login(session, password):
            return RedirectResponse("/", status_code=303)
        return RedirectResponse("/login?error=1", status_code=303)

    @app.post("/logout")
    def logout_submit(session):
        auth_service.logout(session)
        return RedirectResponse("/", status_code=303)
