"""Pure rendering of the admin day dialog and its Holiday, NoTeachWeek, Conference and Lesson forms, per
./day_dialog.sdd."""

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
HOLIDAY_PATH = f"{DIALOG_PATH}/holidays"
NO_TEACH_WEEK_PATH = f"{DIALOG_PATH}/no-teach-weeks"
CONFERENCE_PATH = f"{DIALOG_PATH}/conferences"

# showModal() throws on an already-open dialog, so the reopen is a no-op once the swap has opened it.
_REOPEN_JS = "if (!this.querySelector('dialog[open]')) this.querySelector('dialog').showModal()"
# htmx swaps only 2xx/3xx by default, so a 422 carrying the error form has to opt itself back in.
_ALLOW_ERROR_SWAP_JS = "if (event.detail.xhr.status === 422) event.detail.shouldSwap = true"
_CLOSE_ON_SUCCESS_JS = "if (event.detail.successful) this.closest('dialog').close()"

_INPUT_CLS = "border border-gray-300 rounded px-2 py-1"
_LABEL_CLS = "text-xs font-semibold text-gray-500"
_SAVE_CLS = "bg-blue-600 text-white rounded px-3 py-1"
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
    ("conference", "Conference"),
)


def day_dialog(
    kind: str,
    day: date,
    semester_id: int | None,
    realization_options=(),
    default_no_teach_title: str = "",
    values: dict | None = None,
    error: str = "",
    realization_id: int | None = None,
    holiday=None,
    no_teach_week=None,
    conference=None,
):
    """The dialog for one day, with a tab per kind of entry the admin can add on that day.

    A `realization_id` marks the dialog as opened from that realization's weekly table: the date is editable and a
    successful write re-renders the weekly table instead of the wall planner grid. A Holiday already stored on
    that date, a NoTeachWeek already blocking it and a ../conferences/conferences.sdd Conference already on it replace
    their tab's add form with a prefilled edit form.
    """
    values = values or {}
    return Dialog(
        _tabs(kind, semester_id, day, realization_id),
        Div(f"{day.strftime('%A')}, {dates.format_date(day)}", cls="font-semibold text-sm text-gray-700"),
        _body(
            kind,
            day,
            semester_id,
            realization_options,
            default_no_teach_title,
            values,
            realization_id,
            holiday,
            no_teach_week,
            conference,
        ),
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


def holiday_path(holiday_id: int) -> str:
    """The path of one Holiday's edit route, per ./day_dialog.sdd."""
    return f"{HOLIDAY_PATH}/{holiday_id}"


def holiday_delete_path(holiday_id: int) -> str:
    """The path of one Holiday's delete route, per ./day_dialog.sdd."""
    return f"{holiday_path(holiday_id)}/delete"


def no_teach_week_path(no_teach_week_id: int) -> str:
    """The path of one NoTeachWeek's edit route, per ./day_dialog.sdd."""
    return f"{NO_TEACH_WEEK_PATH}/{no_teach_week_id}"


def no_teach_week_delete_path(no_teach_week_id: int) -> str:
    """The path of one NoTeachWeek's delete route, per ./day_dialog.sdd."""
    return f"{no_teach_week_path(no_teach_week_id)}/delete"


def conference_path(conference_id: int) -> str:
    """The path of one ../conferences/conferences.sdd Conference's edit route, per ./day_dialog.sdd."""
    return f"{CONFERENCE_PATH}/{conference_id}"


def conference_delete_path(conference_id: int) -> str:
    """The path of one Conference's delete route, per ./day_dialog.sdd."""
    return f"{conference_path(conference_id)}/delete"


def holiday_form(day: date, semester_id: int | None, values: dict, realization_id: int | None = None):
    return _form(
        f"{DIALOG_PATH}/holiday",
        day,
        semester_id,
        Span("Title", cls=_LABEL_CLS),
        Input(name="title", value=values.get("title", ""), required=True, cls=_INPUT_CLS),
        realization_id=realization_id,
        editable_day=realization_id is not None,
    )


def no_teach_week_form(day: date, semester_id: int | None, default_no_teach_title: str, values: dict):
    return _form(
        f"{DIALOG_PATH}/no-teach-week",
        day,
        semester_id,
        P(
            "Blocks Monday to Friday of that week; nothing is taught in it.",
            cls="text-xs text-gray-500",
        ),
        Span("Week number", cls=_LABEL_CLS),
        Input(
            name="week_number",
            type="number",
            min="1",
            max="53",
            value=values.get("week_number") or str(day.isocalendar().week),
            required=True,
            cls=_INPUT_CLS,
        ),
        Span("Title", cls=_LABEL_CLS),
        Input(
            name="title",
            value=values.get("title", default_no_teach_title),
            required=True,
            cls=_INPUT_CLS,
        ),
    )


def conference_form(day: date, semester_id: int | None, values: dict, realization_id: int | None = None):
    return _form(
        f"{DIALOG_PATH}/conference",
        day,
        semester_id,
        P(
            "A conference or event that does not necessarily block teaching; "
            "store one per day of a conference that spans several.",
            cls="text-xs text-gray-500",
        ),
        Span("Title", cls=_LABEL_CLS),
        Input(name="title", value=values.get("title", ""), required=True, cls=_INPUT_CLS),
        realization_id=realization_id,
        editable_day=realization_id is not None,
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


def lesson_form(
    day: date,
    semester_id: int | None,
    realization_options,
    values: dict,
    realization_id: int | None = None,
):
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
        Span("CourseRealization", cls=_LABEL_CLS),
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
                Span("Start time", cls=_LABEL_CLS),
                time_select("start_time", values.get("start_time", "08:00"), START_TIME_LATEST),
                cls="flex flex-col gap-1 flex-1",
            ),
            Div(
                Span("End time", cls=_LABEL_CLS),
                time_select("end_time", values.get("end_time", "10:00"), END_TIME_LATEST),
                cls="flex flex-col gap-1 flex-1",
            ),
            cls="flex gap-2",
        ),
        Span("Topic", cls=_LABEL_CLS),
        Input(name="topic", value=values.get("topic", ""), required=True, cls=_INPUT_CLS),
        Span("Notes", cls=_LABEL_CLS),
        Input(name="notes", value=values.get("notes", ""), cls=_INPUT_CLS),
        realization_id=realization_id,
        editable_day=realization_id is not None,
    )


def _form(
    action: str,
    day: date,
    semester_id: int | None,
    *fields,
    realization_id: int | None = None,
    editable_day: bool = False,
    delete: tuple[str, str, int | None] | None = None,
):
    """A form that posts the write and lets the response re-render the whole containing view.

    `delete` is the (path, confirmation, realization_id) of an edit form's `Delete` control, which confirms before
    removing the entry instead of saving it. It carries its own request and swap target, so removing an entry
    re-renders the same containing view the form does instead of swapping into the button itself.
    """
    if editable_day:
        day_fields = (
            Span("Date", cls=_LABEL_CLS),
            layout.day_calendar(day),
        )
    else:
        day_fields = (Input(name="day", type="hidden", value=day.isoformat()),)
    save = Button("Save", type="submit", cls=_SAVE_CLS)
    submit = (
        Button("Save", type="submit", cls=f"mt-3 {_SAVE_CLS}")
        if delete is None
        else Div(save, _delete_button(*delete), cls="flex gap-2 mt-3")
    )
    return Form(
        Input(name="semester_id", type="hidden", value=semester_id),
        Input(name="realization_id", type="hidden", value=realization_id) if realization_id is not None else "",
        *day_fields,
        *fields,
        submit,
        action=action,
        method="post",
        hx_post=action,
        hx_target=f"#{WEEK_TABLE_ID if realization_id is not None else GRID_ID}",
        hx_swap="outerHTML",
        **{
            "hx-on::before-swap": _ALLOW_ERROR_SWAP_JS,
            "hx-on::after-request": _CLOSE_ON_SUCCESS_JS,
        },
        cls="flex flex-col gap-1",
    )


def _delete_button(path: str, confirmation: str, realization_id: int | None = None):
    return Button(
        "Delete",
        type="button",
        hx_post=path,
        hx_confirm=confirmation,
        hx_target=f"#{WEEK_TABLE_ID if realization_id is not None else GRID_ID}",
        hx_swap="outerHTML",
        **{
            "hx-on::before-swap": _ALLOW_ERROR_SWAP_JS,
            "hx-on::after-request": _CLOSE_ON_SUCCESS_JS,
        },
        cls="bg-red-600 text-white rounded px-3 py-1",
    )


def _tabs(kind: str, semester_id: int | None, day: date, realization_id: int | None = None):
    params = {}
    if semester_id is not None:
        params["semester_id"] = semester_id
    params["day"] = day.isoformat()
    if realization_id is not None:
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


def _body(
    kind,
    day,
    semester_id,
    realization_options,
    default_no_teach_title,
    values,
    realization_id: int | None = None,
    holiday=None,
    no_teach_week=None,
    conference=None,
):
    if kind == "no_teach_week":
        if no_teach_week is not None:
            return _no_teach_week_edit_form(no_teach_week, day, semester_id, values, realization_id)
        return no_teach_week_form(day, semester_id, default_no_teach_title, values)
    if kind == "holiday":
        if holiday is not None:
            return _holiday_edit_form(holiday, day, semester_id, values, realization_id)
        return holiday_form(day, semester_id, values, realization_id)
    if kind == "conference":
        if conference is not None:
            return _conference_edit_form(conference, day, semester_id, values, realization_id)
        return conference_form(day, semester_id, values, realization_id)
    return lesson_form(day, semester_id, realization_options, values, realization_id)


def _holiday_edit_form(holiday, day, semester_id, values, realization_id: int | None):
    """The Holiday already on that date, prefilled and deletable, instead of the add form.

    A rejected submission carries its own `holiday_id`, so the block the admin edited is prefilled with what was
    typed and the stored Holiday stays untouched.
    """
    edited = values.get("holiday_id") == holiday.id
    holiday_day = _submitted_day(values, holiday.date) if edited else holiday.date
    title = values.get("title", "") if edited else holiday.title
    return Div(
        P("This day already has a Holiday. Edit it or remove it.", cls="text-xs text-gray-500"),
        _form(
            holiday_path(holiday.id),
            holiday_day,
            semester_id,
            Span("Title", cls=_LABEL_CLS),
            Input(name="title", value=title, required=True, cls=_INPUT_CLS),
            Input(name="holiday_id", type="hidden", value=holiday.id),
            realization_id=realization_id,
            editable_day=True,
            delete=(
                holiday_delete_path(holiday.id),
                f"Delete the Holiday {holiday.title} on {dates.format_date(holiday.date)}?",
                realization_id,
            ),
        ),
    )


def _no_teach_week_edit_form(no_teach_week, day, semester_id, values, realization_id: int | None):
    """The NoTeachWeek already blocking that day, prefilled and deletable, instead of the add form.

    The prefilled week number is the stored one rather than the clicked day's ISO week, so the admin edits what is
    actually blocked.
    """
    edited = values.get("no_teach_week_id") == no_teach_week.id
    week_number = values.get("week_number") if edited else str(no_teach_week.week_number)
    title = values.get("title") if edited else no_teach_week.title
    return Div(
        P(
            f"This day is inside week {no_teach_week.week_number}. Edit or remove that NoTeachWeek.",
            cls="text-xs text-gray-500",
        ),
        _form(
            no_teach_week_path(no_teach_week.id),
            day,
            semester_id,
            P(
                "Blocks Monday to Friday of that week; nothing is taught in it.",
                cls="text-xs text-gray-500",
            ),
            Span("Week number", cls=_LABEL_CLS),
            Input(
                name="week_number",
                type="number",
                min="1",
                max="53",
                value=week_number or str(day.isocalendar().week),
                required=True,
                cls=_INPUT_CLS,
            ),
            Span("Title", cls=_LABEL_CLS),
            Input(name="title", value=title or "", required=True, cls=_INPUT_CLS),
            Input(name="no_teach_week_id", type="hidden", value=no_teach_week.id),
            realization_id=realization_id,
            delete=(
                no_teach_week_delete_path(no_teach_week.id),
                f"Delete the NoTeachWeek in week {no_teach_week.week_number}?",
                realization_id,
            ),
        ),
    )


def _conference_edit_form(conference, day, semester_id, values, realization_id: int | None):
    """The ../conferences/conferences.sdd Conference already on that date, prefilled and deletable, instead of the
    add form.

    A rejected submission carries its own `conference_id`, so the block the admin edited is prefilled with what was
    typed and the stored Conference stays untouched.
    """
    edited = values.get("conference_id") == conference.id
    conference_day = _submitted_day(values, conference.date) if edited else conference.date
    title = values.get("title", "") if edited else conference.title
    return Div(
        P("This day already has a Conference. Edit it or remove it.", cls="text-xs text-gray-500"),
        _form(
            conference_path(conference.id),
            conference_day,
            semester_id,
            Span("Title", cls=_LABEL_CLS),
            Input(name="title", value=title, required=True, cls=_INPUT_CLS),
            Input(name="conference_id", type="hidden", value=conference.id),
            realization_id=realization_id,
            editable_day=True,
            delete=(
                conference_delete_path(conference.id),
                f"Delete the Conference {conference.title} on {dates.format_date(conference.date)}?",
                realization_id,
            ),
        ),
    )


def _submitted_day(values: dict, fallback: date) -> date:
    try:
        return date.fromisoformat(values.get("day", ""))
    except ValueError:
        return fallback
