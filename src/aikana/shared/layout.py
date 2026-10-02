"""The shared page shell: header plus the compiled Tailwind stylesheet and HTMX headers."""

from pathlib import Path

from fasthtml.common import A, Div, H1, Header, Link

STATIC_DIR = Path(__file__).resolve().parent / "static"

_TAILWIND_CSS_HREF = "/static/app.css"

_NAV_LINKS = (
    ("semester", "Semester", "/"),
    ("courses", "Courses", "/courses"),
    ("realizations", "Realizations", "/realizations"),
)


def extra_headers() -> tuple:
    """Extra <head> tags to pass into FastHTML(hdrs=...); HTMX is already added by FastHTML itself."""
    return (Link(rel="stylesheet", href=_TAILWIND_CSS_HREF),)



def _nav(active: str):
    def link(key: str, label: str, href: str):
        cls = "font-semibold text-blue-700" if key == active else "text-gray-600 hover:text-gray-900"
        return A(label, href=href, cls=f"text-sm {cls}")

    return Div(*[link(*entry) for entry in _NAV_LINKS], cls="flex flex-row gap-4")


def page(*content, active_nav: str, selector=None, admin_link=None):
    trailing = [item for item in (selector, admin_link) if item is not None]
    return Div(
        Header(
            H1("Aikana", cls="text-xl font-bold"),
            _nav(active_nav),
            Div(*trailing, cls="ml-auto flex items-center gap-3") if trailing else "",
            cls="flex items-center gap-6 px-4 py-2 border-b border-gray-200",
        ),
        Div(*content, cls="flex-1 min-h-0"),
        cls="h-screen flex flex-col",
    )


