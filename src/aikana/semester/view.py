"""Pure rendering of the semester wall planner (one column per month, one row per day)."""

from fasthtml.common import A, Button, Div, Form, Input, Option, P, Select, Span

from ..day_dialog import view as day_dialog_view
from .services import DayCell, LegendEntry, MonthColumn, SemesterViewModel

# The state a Conference's tooltip states under its title, per ../conferences/conferences.sdd.
_CONFERENCE_STATE = (
    "This conference or event might affect teaching schedule or availability of the teacher"
)


def _tooltip_body(*lines):
    """The `data-tip-body` child of a hover anchor, per ../shared/shared.sdd."""
    return Div(*lines, **{"data-tip-body": ""})


def create_semester_form(error: str = ""):
    return Div(
        Div("Create a Semester to get started.", cls="create-title"),
        Form(
            Select(
                Option("Fall", value="fall"),
                Option("Spring", value="spring"),
                name="term",
                cls="input",
            ),
            Input(
                name="year",
                type="number",
                placeholder="Year",
                required=True,
                cls="input input--year",
            ),
            Button("Create Semester", type="submit", cls="btn"),
            P(error, cls="error") if error else "",
            method="post",
            action="/semesters",
            cls="create-row",
        ),
        cls="create-form",
    )


def no_semester_notice():
    return P("No Semester has been created yet.", cls="notice")


def semester_grid(vm: SemesterViewModel, is_admin: bool):
    """The bare wall-planner grid, without the dialog container, so ../day_dialog/day_dialog.sdd's
    write responses can swap it in under `hx-swap="outerHTML"` without duplicating the container.

    The number of month columns is handed to the stylesheet through the `--months` custom property.
    """
    return Div(
        *[_month_column(month, vm.semester.id, is_admin) for month in vm.months],
        id=day_dialog_view.GRID_ID,
        # The grid is the tooltip area, so a hovered lesson square's tooltip is kept inside it instead of running off
        # the screen at the left-most column or under the header at the first rows.
        **{"data-tip-area": ""},
        style=f"--months: {len(vm.months)};",
        cls="semester-grid",
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
    return Div(*content, cls="semester-view")


def legend_bar(vm: SemesterViewModel):
    """The bar naming the wall planner's markers: one entry per CourseRealization in its own color, then a square
    labelled as a Lesson and a circle labelled as a Deadline.

    The realization entries wrap instead of scrolling and the bar keeps its own height, so up to ten of them leave the
    grid above fully visible.
    """
    return Div(
        Div(
            *[_legend_chip(entry) for entry in vm.legend],
            cls="legend-items",
        ),
        Div(
            _marker(Div(cls="marker marker--lesson marker--plain"), "Lesson"),
            _marker(Div(cls="marker marker--deadline"), "Deadline"),
            cls="legend-markers",
        ),
        cls="legend",
        id="semester-legend",
    )


def _legend_chip(entry: LegendEntry):
    return Div(
        Div(cls="marker marker--lesson", style=f"background-color:{entry.color};"),
        Span(entry.label, cls="legend-chip-label"),
        cls="legend-chip",
    )


def _marker(chip, label: str):
    return Div(chip, Span(label), cls="legend-marker")


def _month_column(month: MonthColumn, semester_id: int, is_admin: bool):
    return Div(
        Div(month.label, cls="month-label"),
        Div(*[_day_row(day, semester_id, is_admin) for day in month.days], cls="days"),
        cls="month",
    )


def _day_row(day: DayCell, semester_id: int, is_admin: bool):
    # A Conference does not block teaching, so its day carries no tint and keeps its lesson squares.
    is_blocked = bool(day.holiday_title or day.no_teach_title)
    modifiers = ["day"]
    if day.day.weekday() >= 5:
        modifiers.append("day--weekend")
    if is_blocked:
        modifiers.append("day--blocked")
    if day.is_today:
        modifiers.append("day--today")
    # Nothing is taught during a NoTeachWeek, so its Monday-to-Friday rows show no lesson squares.
    squares = [] if day.no_teach_title else day.squares
    title = day.holiday_title or day.no_teach_title
    if is_admin:
        # Clicking the row opens the day dialog for this date, per ../day_dialog/day_dialog.sdd. A day that already
        # holds a Conference opens on that tab, since its add form is the one the admin most likely wants there.
        kind = "conference" if day.conference_title else "lesson"
        modifiers.append("day--clickable")
        row_attrs = {
            "hx_get": (
                f"{day_dialog_view.DIALOG_PATH}"
                f"?semester_id={semester_id}&day={day.day.isoformat()}&kind={kind}"
            ),
            "hx_target": f"#{day_dialog_view.CONTAINER_ID}",
            "hx_swap": "innerHTML",
        }
    else:
        row_attrs = {}
    return Div(
        # The week number's gutter is rendered on every row, not only the Mondays that carry one, so the weekday
        # labels stay aligned down the whole column.
        Span(
            str(day.week_number) if day.week_number is not None else "",
            cls="day-week",
        ),
        Span(day.weekday_label, cls="day-weekday"),
        Span(str(day.day.day), cls="day-num"),
        Div(
            # The Lesson squares come first and the ../deadlines/deadlines.sdd circles after them, so a deadline
            # drawn on a day with a Lesson overlaps that square instead of pushing it away.
            *[_lesson_square(square, is_admin) for square in squares],
            *[_deadline_circle(circle, is_admin) for circle in day.circles],
            cls="day-markers",
        ),
        Span(title, cls="day-note") if title else "",
        _conference_title(day.conference_title) if day.conference_title else "",
        cls=" ".join(modifiers),
        **row_attrs,
    )


def _lesson_square(square, is_admin: bool):
    time_range = f"{square.start_time.strftime('%H:%M')}\u2013{square.end_time.strftime('%H:%M')}"
    # A square is a link to the weekly view, so it must not also open the day dialog of the row around it.
    square_attrs = {"hx-on:click": "event.stopPropagation()"} if is_admin else {}
    return A(
        _tooltip_body(
            Div(square.realization_label, cls="tip-title"),
            Div(time_range, cls="tip-sub"),
            Div(square.topic, cls="tip-topic"),
            Div(square.notes, cls="tip-notes") if square.notes else "",
        ),
        href=f"/realizations?realization_id={square.realization_id}",
        cls="marker marker--lesson",
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
            Div(conference_title, cls="tip-title"),
            Div(_CONFERENCE_STATE, cls="tip-sub"),
        ),
        conference_title,
        cls="day-conference",
        **{"data-tip": ""},
    )


def _deadline_circle(circle, is_admin: bool):
    """One ../deadlines/deadlines.sdd Deadline as a donut (a hollow colored ring) on its day row.

    Its ring carries the CourseRealization's square color, the fill is transparent, and it shows the same kind of
    tooltip a Lesson square does and links to that realization's weekly view, so the click must not also open the
    day dialog of the row around it.
    """
    # The circle is a link to the weekly view, so it must not also open the day dialog of the row around it.
    circle_attrs = {"hx-on:click": "event.stopPropagation()"} if is_admin else {}
    return A(
        _tooltip_body(
            Div(circle.title, cls="tip-title"),
            Div(circle.realization_label, cls="tip-sub"),
        ),
        href=f"/realizations?realization_id={circle.realization_id}",
        cls="marker marker--deadline",
        style=f"border-color:{circle.color};",
        # The circle is the tooltip's anchor; the script follows this marker on hover.
        **{"data-tip": ""},
        **circle_attrs,
    )
