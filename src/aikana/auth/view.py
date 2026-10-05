"""Pure rendering of the login form and the shared header's login/logout link."""

from fasthtml.common import A, Button, Form, Input, P


def login_form(error: bool = False):
    return Form(
        Input(
            name="password",
            type="password",
            placeholder="Password",
            cls="input",
        ),
        Button("Log in", type="submit", cls="btn"),
        P("Incorrect password.", cls="error") if error else "",
        method="post",
        action="/login",
        cls="login-form",
    )


def header_link(is_admin: bool):
    if is_admin:
        return Form(
            Button("Log out", type="submit", cls="linkbtn"),
            method="post",
            action="/logout",
        )
    return A("Log in", href="/login", cls="link link--muted")
