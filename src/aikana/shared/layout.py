"""The shared page shell: header plus the Tailwind Play CDN and HTMX headers."""

from fasthtml.common import Div, H1, Header, Script

_TAILWIND_CDN_SRC = "https://cdn.tailwindcss.com"


def extra_headers() -> tuple:
    """Extra <head> tags to pass into FastHTML(hdrs=...); HTMX is already added by FastHTML itself."""
    return (Script(src=_TAILWIND_CDN_SRC),)


def page(*content):
    return Div(
        Header(
            H1("Aikana", cls="text-xl font-bold"),
            # TODO: show a login link for visitors and a logout link for the admin once ../auth/auth.sdd exists.
            cls="flex items-center justify-between px-4 py-2 border-b border-gray-200",
        ),
        Div(*content, cls="flex-1 min-h-0"),
        cls="h-screen flex flex-col",
    )
