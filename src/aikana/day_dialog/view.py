"""Pure rendering of the admin day dialog and its Holiday, NoTeachWeek and Lesson forms, per ./day_dialog.sdd."""

from datetime import date
from urllib.parse import urlencode

from fasthtml.common import Button, Dialog, Div, Form, Input, Option, P, Select, Span

# The containing view renders dialog_container() once and never replaces it, so its hx-on::after-swap handler stays
# attached and re-opens the <dialog> that every dialog response swaps into it. The response must therefore be the
# bare <dialog>, never this container, or an innerHTML swap would nest a second element under the same id.
CONTAINER_ID = "day-dialog"
DIALOG_ID = "day-dialog-modal"
GRID_ID = "semester-grid"
DIALOG_PATH = "/day/dialog"

# showModal() throws on an already-open dialog, so the reopen is a no-op once the swap has opened it.
_REOPEN_JS = "if (!this.querySelector('dialog[open]')) this.querySelector('dialog').showModal()"
# htmx swaps only 2xx/3xx by default, so a 422 carrying the error form has to opt itself back in.
_ALLOW_ERROR_SWAP_JS = "if (event.detail.xhr.status === 422) event.detail.shouldSwap = true"
_CLOSE_ON_SUCCESS_JS = "if (event.detail.successful) this.closest('dialog').close()"

_INPUT_CLS = "border border-gray-300 rounded px-2 py-1"
_TIME_PATTERN = r"([01][0-9]|2[0-3]):[0-5][0-9]"
_TAB_CLS = "rounded px-2 py-1 text-sm"
_ACTIVE_TAB_CLS = "bg-blue-600 text-white"
_TABS = (
    ("holiday", "Holiday"),
    ("no_teach_week", "NoTeachWeek"),
    ("lesson", "Lesson"),
)


def day_dialog(
    kind: str,
    day: date,
    semester_id: str,
    realization_options=(),
    default_no_teach_title: str = "",
    values: dict | None = None,
    error: str = "",
):
    """The dialog for one day, with a tab per kind of entry the admin can add on that day."""
    values = values or {}
    return Dialog(
        _tabs(kind, semester_id, day),
        Div(day.strftime("%A, %d %B %Y"), cls="font-semibold text-sm text-gray-700"),
        _body(kind, day, semester_id, realization_options, default_no_teach_title, values),
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


def holiday_form(day: date, semester_id: str, values: dict):
    return _form(
        f"{DIALOG_PATH}/holiday",
        day,
        semester_id,
        Span("Title", cls="text-xs font-semibold text-gray-500"),
        Input(name="title", value=values.get("title", ""), required=True, cls=_INPUT_CLS),
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


def lesson_form(day: date, semester_id: str, realization_options, values: dict):
    options = list(realization_options)
    if not options:
        return P("No CourseRealizations in this Semester yet.", cls="text-sm text-gray-500")
    selected = values.get("course_realization_id") or options[0][0]
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
        Span("Start time", cls="text-xs font-semibold text-gray-500"),
        Input(
            name="start_time",
            value=values.get("start_time", "08:00"),
            required=True,
            pattern=_TIME_PATTERN,
            placeholder="HH:MM",
            maxlength="5",
            cls=_INPUT_CLS,
        ),
        Span("End time", cls="text-xs font-semibold text-gray-500"),
        Input(
            name="end_time",
            value=values.get("end_time", "10:00"),
            required=True,
            pattern=_TIME_PATTERN,
            placeholder="HH:MM",
            maxlength="5",
            cls=_INPUT_CLS,
        ),
        Span("Topic", cls="text-xs font-semibold text-gray-500"),
        Input(name="topic", value=values.get("topic", ""), required=True, cls=_INPUT_CLS),
        Span("Notes", cls="text-xs font-semibold text-gray-500"),
        Input(name="notes", value=values.get("notes", ""), cls=_INPUT_CLS),
    )


def _form(action: str, day: date, semester_id: str, *fields):
    """A form that posts the write and lets the response re-render the whole wall planner."""
    return Form(
        Input(name="semester_id", type="hidden", value=semester_id),
        Input(name="day", type="hidden", value=day.isoformat()),
        *fields,
        Button("Save", type="submit", cls="mt-3 bg-blue-600 text-white rounded px-3 py-1"),
        action=action,
        method="post",
        hx_post=action,
        hx_target=f"#{GRID_ID}",
        hx_swap="outerHTML",
        **{
            "hx-on::before-swap": _ALLOW_ERROR_SWAP_JS,
            "hx-on::after-request": _CLOSE_ON_SUCCESS_JS,
        },
        cls="flex flex-col gap-1",
    )


def _tabs(kind: str, semester_id: str, day: date):
    return Div(
        *[
            Button(
                label,
                type="button",
                hx_get=f"{DIALOG_PATH}?{urlencode({'semester_id': semester_id, 'day': day.isoformat(), 'kind': tab_kind})}",
                hx_target=f"#{CONTAINER_ID}",
                hx_swap="innerHTML",
                cls=f"{_TAB_CLS} {_ACTIVE_TAB_CLS if tab_kind == kind else 'text-gray-600 hover:bg-gray-100'}",
            )
            for tab_kind, label in _TABS
        ],
        cls="flex gap-1 mb-3 border-b border-gray-200 pb-2",
    )


def _body(kind, day, semester_id, realization_options, default_no_teach_title, values):
    if kind == "no_teach_week":
        return no_teach_week_form(day, semester_id, default_no_teach_title, values)
    if kind == "lesson":
        return lesson_form(day, semester_id, realization_options, values)
    return holiday_form(day, semester_id, values)
