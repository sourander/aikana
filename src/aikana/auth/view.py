"""Pure rendering of the login form and the shared header's login/logout link."""

from fasthtml.common import A, Button, Form, Input, P


def login_form(error: bool = False):
    return Form(
        Input(
            name="password",
            type="password",
            placeholder="Password",
            cls="border border-gray-300 rounded px-2 py-1",
        ),
        Button("Log in", type="submit", cls="bg-blue-600 text-white rounded px-3 py-1"),
        P("Incorrect password.", cls="text-red-600 text-sm") if error else "",
        method="post",
        action="/login",
        cls="flex flex-col gap-2 p-4 max-w-xs",
    )


def header_link(is_admin: bool):
    if is_admin:
        return Form(
            Button("Log out", type="submit", cls="text-sm text-gray-600 hover:text-gray-900"),
            method="post",
            action="/logout",
        )
    return A("Log in", href="/login", cls="text-sm text-gray-600 hover:text-gray-900")
