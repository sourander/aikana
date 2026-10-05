"""The shared page shell: header plus the compiled Tailwind stylesheet and HTMX headers."""

from datetime import date
from pathlib import Path

from fasthtml.common import A, Div, H1, Header, Input, Label, Link, Option, Script, Select, Span

from . import dates

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

# A hover tooltip anchored to a tiny target (a lesson square, a colored dot) cannot know from CSS alone whether it
# fits on screen, so this script moves it: centred on the target, flipped below it when there is no room above and
# clamped inside the tooltip's area, so it never leaves the viewport or slides under a top bar.
_TOOLTIP_JS = """
(function () {
  var GAP = 6;

  function clamp(value, min, max) {
    if (max < min) return min;
    return Math.min(Math.max(value, min), max);
  }

  function measure(tip) {
    var display = tip.style.display;
    var visibility = tip.style.visibility;
    tip.style.display = "flex";
    tip.style.visibility = "hidden";
    var box = tip.getBoundingClientRect();
    tip.style.display = display;
    tip.style.visibility = visibility;
    return box;
  }

  function place(target) {
    var tip = target.querySelector("[data-tip-body]");
    if (!tip) return;
    var box = measure(tip);
    if (!box.width || !box.height) return;
    var targetBox = target.getBoundingClientRect();
    var area = target.closest("[data-tip-area]");
    var limits = area ? area.getBoundingClientRect() : document.documentElement.getBoundingClientRect();
    var left = clamp(targetBox.left + targetBox.width / 2 - box.width / 2,
      limits.left + GAP, limits.right - GAP - box.width);
    var top = targetBox.top - box.height - GAP;
    if (top < limits.top + GAP) {
      top = Math.min(targetBox.bottom + GAP, limits.bottom - GAP - box.height);
    }
    tip.style.left = left - targetBox.left + "px";
    tip.style.top = clamp(top, limits.top + GAP, limits.bottom - GAP - box.height) - targetBox.top + "px";
    tip.style.bottom = "auto";
    // Tailwind 4 centres a tooltip through the `translate` property, not `transform`, so cancel both.
    tip.style.transform = "none";
    tip.style.translate = "none";
    tip.style.margin = "0";
  }

  document.addEventListener("mouseover", function (event) {
    var target = event.target instanceof Element ? event.target.closest("[data-tip]") : null;
    if (target) place(target);
  });
})();
"""


def extra_headers() -> tuple:
    """Extra <head> tags to pass into FastHTML(hdrs=...); HTMX is already added by FastHTML itself."""
    return (Link(rel="stylesheet", href=_TAILWIND_CSS_HREF), Script(_TOOLTIP_JS))


def dropdown(
    name: str,
    options: list[tuple[int, str]],
    selected_id: int | None,
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


def day_calendar(selected: date, name: str = "day"):
    """A Monday-first month grid of `selected`'s month whose day cells are the form's own radio buttons.

    The browser's native date picker starts its week on Sunday in many locales and cannot be re-ordered, so the app
    renders the grid itself; the selection needs no script because each cell is a `name` radio input.
    """
    return Div(
        Div(
            *[
                Span(weekday, cls="flex h-7 w-8 items-center justify-center text-xs text-gray-500")
                for weekday in dates.MONDAY_FIRST_WEEKDAYS
            ],
            cls="grid grid-cols-7 gap-1",
        ),
        *[
            Div(
                *[_calendar_day(day, selected, name) for day in week],
                cls="grid grid-cols-7 gap-1",
            )
            for week in dates.month_grid(selected)
        ],
        cls="w-max",
    )


def _calendar_day(day: date | None, selected: date, name: str):
    if day is None:
        return Span("", cls="h-8 w-8")
    return Label(
        Input(
            type="radio",
            name=name,
            value=day.isoformat(),
            checked=(day == selected),
            cls="peer sr-only",
        ),
        Span(
            str(day.day),
            cls="flex h-8 w-8 items-center justify-center rounded text-sm hover:bg-gray-100"
            " peer-checked:bg-blue-600 peer-checked:text-white peer-focus-visible:ring-2",
        ),
        cls="contents",
    )


def _nav(active: str, selected_semester_id: int | None):
    def link(key: str, label: str, href: str):
        cls = "font-semibold text-blue-700" if key == active else "text-gray-600 hover:text-gray-900"
        if selected_semester_id is not None:
            href = f"{href}?semester_id={selected_semester_id}"
        # The label stays on one line, so a narrow viewport wraps the nav onto a further header line instead of
        # breaking a label across two.
        return A(label, href=href, cls=f"text-sm whitespace-nowrap {cls}")

    return Div(*[link(*entry) for entry in _NAV_LINKS], cls="flex flex-row gap-4")


def page(
    *content,
    active_nav: str,
    semester_options: list[tuple[int, str]] = (),
    selected_semester_id: int | None = None,
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
            # The header's groups wrap onto further lines when the viewport is too narrow for one, so nothing is
            # squeezed or broken mid-label on a phone-sized screen.
            H1("Aikana", cls="text-xl font-bold whitespace-nowrap"),
            _nav(active_nav, selected_semester_id),
            Div(*trailing, cls="ml-auto flex items-center gap-3") if trailing else "",
            cls="flex flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2 border-b border-gray-200",
        ),
        Div(*content, cls="flex-1 min-h-0"),
        cls="h-screen flex flex-col",
    )
