"""The shared page shell: header plus the compiled Tailwind stylesheet and HTMX headers."""

from pathlib import Path

from fasthtml.common import A, Div, H1, Header, Link, Option, Script, Select

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
