"""Pure rendering of the admin day dialog and its Holiday, NoTeachWeek and Lesson forms, per ./day_dialog.sdd."""

from datetime import date, time
from urllib.parse import urlencode

from fasthtml.common import Button, Dialog, Div, Form, Input, Option, P, Select, Span

from ..shared import dates, layout

# The containing view renders dialog_container() once and never replaces it, so its hx-on::after-swap handler stays
# attached and re-opens the <dialog> that every dialog response swaps into it. The response must therefore be the
# bare <dialog>, never this container, or an innerHTML swap would nest a second element under the same id.
CONTAINER_ID = "day-dialog"
DIALOG_ID = "day-dialog-modal"
GRID_ID = "semester-grid"
WEEK_TABLE_ID = "realization-week-table"
DIALOG_PATH = "/day/dialog"

# showModal() throws on an already-open dialog, so the reopen is a no-op once the swap has opened it.
_REOPEN_JS = "if (!this.querySelector('dialog[open]')) this.querySelector('dialog').showModal()"
# htmx swaps only 2xx/3xx by default, so a 422 carrying the error form has to opt itself back in.
_ALLOW_ERROR_SWAP_JS = "if (event.detail.xhr.status === 422) event.detail.shouldSwap = true"
_CLOSE_ON_SUCCESS_JS = "if (event.detail.successful) this.closest('dialog').close()"

_INPUT_CLS = "border border-gray-300 rounded px-2 py-1"
# Lessons are always taught between 08:00 and 21:00 and start on a quarter hour, so the Lesson forms offer
# only those times instead of free text.
START_TIME_LATEST = "20:45"
END_TIME_LATEST = "21:00"
_TIME_VALUES = tuple(f"{hour:02d}:{minute:02d}" for hour in range(8, 22) for minute in (0, 15, 30, 45))
_TAB_CLS = "rounded px-2 py-1 text-sm"
_ACTIVE_TAB_CLS = "bg-blue-600 text-white"
_TABS = (
    ("lesson", "Lesson"),
    ("holiday", "Holiday"),
    ("no_teach_week", "NoTeachWeek"),
)


def day_dialog(
    kind: str,
    day: date,
    semester_id: str,
    realization_options=(),
    default_no_teach_title: str = "",
    values: dict | None = None,
    error: str = "",
    realization_id: str = "",
):
    """The dialog for one day, with a tab per kind of entry the admin can add on that day.

    A `realization_id` marks the dialog as opened from that realization's weekly table: the date is editable and a
    successful write re-renders the weekly table instead of the wall planner grid.
    """
    values = values or {}
    return Dialog(
        _tabs(kind, semester_id, day, realization_id),
        Div(f"{day.strftime('%A')}, {dates.format_date(day)}", cls="font-semibold text-sm text-gray-700"),
        _body(kind, day, semester_id, realization_options, default_no_teach_title, values, realization_id),
        P(error, cls="text-red-600 text-sm mt-2") if error else "",
        Button(
            "Close",
            type="button",
            onclick="this.closest('dialog').close()",
            cls="mt-3 border border-gray-300 rounded px-3 py-1 text-sm",
        ),
        id=DIALOG_ID,
        cls="rounded p-4 w-96",
    )


def dialog_container():
    """The stable element every dialog response is swapped into, per ./day_dialog.sdd."""
    return Div(id=CONTAINER_ID, **{"hx-on::after-swap": _REOPEN_JS})


def holiday_form(day: date, semester_id: str, values: dict, realization_id: str = ""):
    return _form(
        f"{DIALOG_PATH}/holiday",
        day,
        semester_id,
        Span("Title", cls="text-xs font-semibold text-gray-500"),
        Input(name="title", value=values.get("title", ""), required=True, cls=_INPUT_CLS),
        realization_id=realization_id,
        editable_day=bool(realization_id),
    )


def no_teach_week_form(day: date, semester_id: str, default_no_teach_title: str, values: dict):
    return _form(
        f"{DIALOG_PATH}/no-teach-week",
        day,
        semester_id,
        P(
            "Blocks Monday to Friday of that week; nothing is taught in it.",
            cls="text-xs text-gray-500",
        ),
        Span("Week number", cls="text-xs font-semibold text-gray-500"),
        Input(
            name="week_number",
            type="number",
            min="1",
            max="53",
            value=values.get("week_number") or str(day.isocalendar().week),
            required=True,
            cls=_INPUT_CLS,
        ),
        Span("Title", cls="text-xs font-semibold text-gray-500"),
        Input(
            name="title",
            value=values.get("title", default_no_teach_title),
            required=True,
            cls=_INPUT_CLS,
        ),
    )


def time_select(name: str, selected: str, latest: str):
    """A dropdown of 24-hour `HH:MM` values on a 15-minute grid from `08:00` to `latest`.

    A valid time outside the grid is kept as an option when it is already the selected value, so editing a stored
    Lesson never silently moves its time onto the grid.
    """
    values = [value for value in _TIME_VALUES if value <= latest]
    if selected and selected not in values and selected <= latest:
        try:
            time.fromisoformat(selected)
        except ValueError:
            pass
        else:
            values.append(selected)
            values.sort()
    return Select(
        *[Option(value, value=value, selected=(value == selected)) for value in values],
        name=name,
        required=True,
        cls=f"{_INPUT_CLS} w-full",
    )


def lesson_form(day: date, semester_id: str, realization_options, values: dict, realization_id: str = ""):
    options = list(realization_options)
    if not options:
        return P("No CourseRealizations in this Semester yet.", cls="text-sm text-gray-500")
    option_ids = [option_id for option_id, _ in options]
    selected = values.get("course_realization_id") or (
        realization_id if realization_id in option_ids else options[0][0]
    )
    return _form(
        f"{DIALOG_PATH}/lesson",
        day,
        semester_id,
        Span("CourseRealization", cls="text-xs font-semibold text-gray-500"),
        Select(
            *[
                Option(label, value=option_id, selected=(option_id == selected))
                for option_id, label in options
            ],
            name="course_realization_id",
            cls=_INPUT_CLS,
        ),
        Div(
            Div(
                Span("Start time", cls="text-xs font-semibold text-gray-500"),
                time_select("start_time", values.get("start_time", "08:00"), START_TIME_LATEST),
                cls="flex flex-col gap-1 flex-1",
            ),
            Div(
                Span("End time", cls="text-xs font-semibold text-gray-500"),
                time_select("end_time", values.get("end_time", "10:00"), END_TIME_LATEST),
                cls="flex flex-col gap-1 flex-1",
            ),
            cls="flex gap-2",
        ),
        Span("Topic", cls="text-xs font-semibold text-gray-500"),
        Input(name="topic", value=values.get("topic", ""), required=True, cls=_INPUT_CLS),
        Span("Notes", cls="text-xs font-semibold text-gray-500"),
        Input(name="notes", value=values.get("notes", ""), cls=_INPUT_CLS),
        realization_id=realization_id,
        editable_day=bool(realization_id),
    )


def _form(action: str, day: date, semester_id: str, *fields, realization_id: str = "", editable_day: bool = False):
    """A form that posts the write and lets the response re-render the whole containing view."""
    if editable_day:
        day_fields = (
            Span("Date", cls="text-xs font-semibold text-gray-500"),
            layout.day_calendar(day),
        )
    else:
        day_fields = (Input(name="day", type="hidden", value=day.isoformat()),)
    return Form(
        Input(name="semester_id", type="hidden", value=semester_id),
        Input(name="realization_id", type="hidden", value=realization_id) if realization_id else "",
        *day_fields,
        *fields,
        Button("Save", type="submit", cls="mt-3 bg-blue-600 text-white rounded px-3 py-1"),
        action=action,
        method="post",
        hx_post=action,
        hx_target=f"#{WEEK_TABLE_ID if realization_id else GRID_ID}",
        hx_swap="outerHTML",
        **{
            "hx-on::before-swap": _ALLOW_ERROR_SWAP_JS,
            "hx-on::after-request": _CLOSE_ON_SUCCESS_JS,
        },
        cls="flex flex-col gap-1",
    )


def _tabs(kind: str, semester_id: str, day: date, realization_id: str = ""):
    params = {"semester_id": semester_id, "day": day.isoformat()}
    if realization_id:
        params["realization_id"] = realization_id
    return Div(
        *[
            Button(
                label,
                type="button",
                hx_get=f"{DIALOG_PATH}?{urlencode({**params, 'kind': tab_kind})}",
                hx_target=f"#{CONTAINER_ID}",
                hx_swap="innerHTML",
                cls=f"{_TAB_CLS} {_ACTIVE_TAB_CLS if tab_kind == kind else 'text-gray-600 hover:bg-gray-100'}",
            )
            for tab_kind, label in _TABS
        ],
        cls="flex gap-1 mb-3 border-b border-gray-200 pb-2",
    )


def _body(kind, day, semester_id, realization_options, default_no_teach_title, values, realization_id: str = ""):
    if kind == "no_teach_week":
        return no_teach_week_form(day, semester_id, default_no_teach_title, values)
    if kind == "lesson":
        return lesson_form(day, semester_id, realization_options, values, realization_id)
    return holiday_form(day, semester_id, values, realization_id)
