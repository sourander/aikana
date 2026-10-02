"""The shared page shell: header plus the compiled Tailwind stylesheet and HTMX headers."""

from pathlib import Path

from fasthtml.common import A, Div, H1, Header, Link, Option, Select

STATIC_DIR = Path(__file__).resolve().parent / "static"

_TAILWIND_CSS_HREF = "/static/app.css"

_NAV_LINKS = (
    ("semester", "Semester", "/"),
    ("courses", "Courses", "/courses"),
    ("realizations", "Realizations", "/realizations"),
)

_NAV_HREFS = {key: href for key, _, href in _NAV_LINKS}

_SELECT_CLS = "border border-gray-300 rounded text-sm px-2 py-1"

SEMESTER_SELECT_ID = "semester-select"


def extra_headers() -> tuple:
    """Extra <head> tags to pass into FastHTML(hdrs=...); HTMX is already added by FastHTML itself."""
    return (Link(rel="stylesheet", href=_TAILWIND_CSS_HREF),)


def dropdown(
    name: str,
    options: list[tuple[str, str]],
    selected_id: str,
    hx_get: str,
    hx_include: str = "",
    select_id: str = "",
):
    """A header select that re-renders `hx_get` with its own value when changed."""
    return Select(
        *[Option(label, value=option_id, selected=(option_id == selected_id)) for option_id, label in options],
        name=name,
        id=select_id or None,
        hx_get=hx_get,
        hx_trigger="change",
        hx_target="body",
        hx_push_url="true",
        hx_include=hx_include or None,
        cls=_SELECT_CLS,
    )


def _nav(active: str, selected_semester_id: str):
    def link(key: str, label: str, href: str):
        cls = "font-semibold text-blue-700" if key == active else "text-gray-600 hover:text-gray-900"
        if selected_semester_id:
            href = f"{href}?semester_id={selected_semester_id}"
        return A(label, href=href, cls=f"text-sm {cls}")

    return Div(*[link(*entry) for entry in _NAV_LINKS], cls="flex flex-row gap-4")


def page(
    *content,
    active_nav: str,
    semester_options: list[tuple[str, str]] = (),
    selected_semester_id: str = "",
    selector=None,
    admin_link=None,
):
    semester_selector = None
    if semester_options:
        semester_selector = dropdown(
            "semester_id",
            semester_options,
            selected_semester_id,
            _NAV_HREFS.get(active_nav, "/"),
            select_id=SEMESTER_SELECT_ID,
        )

    trailing = [item for item in (semester_selector, selector, admin_link) if item is not None]
    return Div(
        Header(
            H1("Aikana", cls="text-xl font-bold"),
            _nav(active_nav, selected_semester_id),
            Div(*trailing, cls="ml-auto flex items-center gap-3") if trailing else "",
            cls="flex items-center gap-6 px-4 py-2 border-b border-gray-200",
        ),
        Div(*content, cls="flex-1 min-h-0"),
        cls="h-screen flex flex-col",
    )
