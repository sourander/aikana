"""Pure rendering of the semester wall planner (one column per month, one row per day)."""

from fasthtml.common import A, Button, Div, Form, Input, Option, P, Select, Span

from ..day_dialog import view as day_dialog_view
from .services import DayCell, LegendEntry, MonthColumn, SemesterViewModel

# A day row needs room for its week-number gutter, weekday abbreviation, date number and lesson squares, so a month
# column never gets narrower than this. A viewport too narrow for every column scrolls the grid instead of squeezing
# the labels out of sight, per ./semester.sdd.
_DAY_MIN_WIDTH = "8rem"

# The tooltip body every hover anchor carries, positioned above its anchor by these classes;
# ../shared/shared.sdd's script moves it inside the grid when it would not fit there.
_TOOLTIP_CLS = (
    "pointer-events-none absolute left-1/2 -translate-x-1/2 bottom-full mb-1 hidden w-56 "
    "flex-col gap-0.5 whitespace-normal break-words rounded-lg border border-gray-200 bg-white "
    "p-3 text-xs leading-snug shadow-lg group-hover:flex z-20"
)

# The state a Conference's tooltip states under its title, per ../conferences/conferences.sdd.
_CONFERENCE_STATE = (
    "This conference or event might affect teaching schedule or availability of the teacher"
)


def _tooltip_body(*lines):
    """The `data-tip-body` child of a hover anchor, per ../shared/shared.sdd."""
    return Div(*lines, **{"data-tip-body": ""}, cls=_TOOLTIP_CLS)


def create_semester_form(error: str = ""):
    return Div(
        Div("Create a Semester to get started.", cls="font-semibold text-lg mb-2"),
        Form(
            Select(
                Option("Fall", value="fall"),
                Option("Spring", value="spring"),
                name="term",
                cls="border border-gray-300 rounded px-2 py-1",
            ),
            Input(
                name="year",
                type="number",
                placeholder="Year",
                required=True,
                cls="border border-gray-300 rounded px-2 py-1 w-24",
            ),
            Button("Create Semester", type="submit", cls="bg-blue-600 text-white rounded px-3 py-1"),
            P(error, cls="text-red-600 text-sm") if error else "",
            method="post",
            action="/semesters",
            cls="flex items-center gap-2",
        ),
        cls="p-4",
    )


def no_semester_notice():
    return P("No Semester has been created yet.", cls="p-4 text-sm text-gray-500")


def new_semester_control():
    return A("+ New Semester", href="/semesters/new", cls="text-sm text-blue-700 hover:text-blue-900")


def semester_grid(vm: SemesterViewModel, is_admin: bool):
    """The bare wall-planner grid, without the dialog container, so ../day_dialog/day_dialog.sdd's
    write responses can swap it in under `hx-swap="outerHTML"` without duplicating the container."""
    return Div(
        *[_month_column(month, vm.semester.id, is_admin) for month in vm.months],
        id=day_dialog_view.GRID_ID,
        # The grid is the tooltip area, so a hovered lesson square's tooltip is kept inside it instead of running off
        # the screen at the left-most column or under the header at the first rows.
        **{"data-tip-area": ""},
        # The grid scrolls in both directions rather than clipping, so a viewport too narrow for the columns' minimum
        # widths scrolls sideways and rows too tall for the container scroll down, per ./semester.sdd.
        style=f"display:grid; grid-template-columns:repeat({len(vm.months)}, 1fr); gap:10px; "
        "height:100%; overflow:auto;",
        cls="p-4",
    )


def semester_view(vm: SemesterViewModel, is_admin: bool = False):
    """The wall planner: the grid, the legend bar below it and, for the admin, the day dialog's container.

    The legend bar is a sibling of the grid and not part of @semester_grid, so a ../day_dialog/day_dialog.sdd write
    swapping `outerHTML` into the grid leaves the bar in place. A day dialog can only add a Lesson, a Holiday, a
    NoTeachWeek or a Conference, so the bar's realizations cannot go stale under a swap.
    """
    content = [semester_grid(vm, is_admin), legend_bar(vm)]
    if is_admin:
        content.append(day_dialog_view.dialog_container())
    return Div(*content, cls="h-full min-h-0 flex flex-col")


def legend_bar(vm: SemesterViewModel):
    """The bar naming the wall planner's markers: one entry per CourseRealization in its own color, then a square
    labelled as a Lesson and a circle labelled as a Deadline.

    The realization entries wrap instead of scrolling and the bar keeps its own height, so up to ten of them leave the
    grid above fully visible.
    """
    return Div(
        Div(
            *[_legend_chip(entry) for entry in vm.legend],
            cls="flex flex-1 flex-wrap items-center gap-x-4 gap-y-1 min-w-0",
        ),
        Div(
            _marker(Div(cls="w-3 h-3 rounded-sm bg-gray-400 shrink-0"), "Lesson"),
            _marker(Div(cls="w-3 h-3 rounded-full bg-gray-400 opacity-50 shrink-0"), "Deadline"),
            cls="flex shrink-0 items-center gap-4 border-l border-gray-200 pl-4 ml-4",
        ),
        cls="flex shrink-0 items-start gap-4 border-t border-gray-200 px-4 py-2 text-xs text-gray-600",
        id="semester-legend",
    )


def _legend_chip(entry: LegendEntry):
    return Div(
        Div(cls="w-3 h-3 rounded-sm shrink-0", style=f"background-color:{entry.color};"),
        Span(entry.label, cls="truncate"),
        cls="flex min-w-0 items-center gap-1",
    )


def _marker(chip, label: str):
    return Div(chip, Span(label, cls="whitespace-nowrap"), cls="flex shrink-0 items-center gap-1")


def _month_column(month: MonthColumn, semester_id: int, is_admin: bool):
    return Div(
        Div(month.label, cls="font-semibold text-center border-b border-gray-300 pb-1 mb-1"),
        Div(*[_day_row(day, semester_id, is_admin) for day in month.days], cls="flex-1 flex flex-col min-h-0"),
        # The column carries the same minimum width as its day rows, so the grid track cannot collapse below it and one
        # column's rows never overlap the next column.
        style=f"display:flex; flex-direction:column; min-width:{_DAY_MIN_WIDTH};",
    )


def _day_row(day: DayCell, semester_id: int, is_admin: bool):
    # A Conference does not block teaching, so its day carries no tint and keeps its lesson squares.
    is_blocked = bool(day.holiday_title or day.no_teach_title)
    tint_cls = "bg-red-50" if is_blocked or day.day.weekday() >= 5 else ""
    today_cls = "border-l-4 border-l-green-500" if day.is_today else ""
    # Nothing is taught during a NoTeachWeek, so its Monday-to-Friday rows show no lesson squares.
    squares = [] if day.no_teach_title else day.squares
    title = day.holiday_title or day.no_teach_title
    row_cls = f"flex items-center gap-1 border-b border-gray-100 {tint_cls} {today_cls}"
    if is_admin:
        # Clicking the row opens the day dialog for this date, per ../day_dialog/day_dialog.sdd. A day that already
        # holds a Conference opens on that tab, since its add form is the one the admin most likely wants there.
        kind = "conference" if day.conference_title else "lesson"
        row_attrs = {
            "hx_get": (
                f"{day_dialog_view.DIALOG_PATH}"
                f"?semester_id={semester_id}&day={day.day.isoformat()}&kind={kind}"
            ),
            "hx_target": f"#{day_dialog_view.CONTAINER_ID}",
            "hx_swap": "innerHTML",
            "cls": f"{row_cls} cursor-pointer hover:bg-gray-100",
        }
    else:
        row_attrs = {"cls": row_cls}
    return Div(
        # The week number's gutter is rendered on every row, not only the Mondays that carry one, so the weekday
        # labels stay aligned down the whole column.
        Span(
            str(day.week_number) if day.week_number is not None else "",
            cls="w-6 text-xs text-gray-300 text-center shrink-0",
        ),
        Span(day.weekday_label, cls="w-8 text-xs text-gray-500 shrink-0"),
        Span(str(day.day.day), cls="w-5 text-sm shrink-0"),
        Div(
            # The Lesson squares come first and the ../deadlines/deadlines.sdd circles after them, so a deadline
            # drawn on a day with a Lesson overlaps that square instead of pushing it away.
            *[_lesson_square(square, is_admin) for square in squares],
            *[_deadline_circle(circle, is_admin) for circle in day.circles],
            cls="flex-1 flex items-center gap-1 flex-wrap",
        ),
        Span(title, cls="text-xs text-red-600 truncate pr-2") if title else "",
        _conference_title(day.conference_title) if day.conference_title else "",
        style=f"flex:1; min-width:{_DAY_MIN_WIDTH};",
        **row_attrs,
    )


def _lesson_square(square, is_admin: bool):
    time_range = f"{square.start_time.strftime('%H:%M')}\u2013{square.end_time.strftime('%H:%M')}"
    # A square is a link to the weekly view, so it must not also open the day dialog of the row around it.
    square_attrs = {"hx-on:click": "event.stopPropagation()"} if is_admin else {}
    return A(
        _tooltip_body(
            Div(square.realization_label, cls="font-semibold text-gray-900"),
            Div(time_range, cls="text-gray-500"),
            Div(square.topic, cls="text-gray-800"),
            Div(square.notes, cls="text-gray-400 italic mt-1") if square.notes else "",
        ),
        href=f"/realizations?realization_id={square.realization_id}",
        cls="group relative inline-block w-3 h-3 rounded-sm",
        style=f"background-color:{square.color};",
        # The square is the tooltip's anchor; the script follows this marker on hover.
        **{"data-tip": ""},
        **square_attrs,
    )


def _conference_title(conference_title: str):
    """One ../conferences/conferences.sdd Conference as purple text on its day row.

    The text is the tooltip's anchor and carries the title over the state a Conference states, so the row height
    does not change on hover. Clicking it is left to the row around it, which opens the day dialog.
    """
    return Span(
        _tooltip_body(
            Div(conference_title, cls="font-semibold text-gray-900"),
            Div(_CONFERENCE_STATE, cls="text-gray-500"),
        ),
        conference_title,
        cls="group relative inline-block text-xs text-purple-600 truncate pr-2",
        **{"data-tip": ""},
    )


def _deadline_circle(circle, is_admin: bool):
    """One ../deadlines/deadlines.sdd Deadline as a half-transparent circle on its day row.

    It shares the CourseRealization's square color and links to that realization's weekly view exactly as that
    realization's lesson squares do, so the click must not also open the day dialog of the row around it.
    """
    # The circle is a link to the weekly view, so it must not also open the day dialog of the row around it.
    circle_attrs = {"hx-on:click": "event.stopPropagation()"} if is_admin else {}
    return A(
        title=circle.title,
        href=f"/realizations?realization_id={circle.realization_id}",
        cls="inline-block w-3 h-3 rounded-full",
        style=f"background-color:{circle.color}; opacity:0.5;",
        **circle_attrs,
    )
