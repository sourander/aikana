"""Pure rendering of the per-CourseRealization weekly table, its realization selector and, for the admin, the
clickable Lesson sub-rows with their edit and delete dialogs, the empty Lesson add slot of every week, the per-week
deadline controls and the per-week theme dialogs with their dialogs, per ./realizations.sdd.
"""

from fasthtml.common import (
    A,
    Button,
    Dialog,
    Div,
    Form,
    Input,
    P,
    Span,
    Table,
    Tbody,
    Td,
    Th,
    Thead,
    Tr,
)

from ..day_dialog import view as day_dialog_view
from ..shared import dates, layout
from .services import DeadlineEntry, RealizationViewModel, WeekEntry, WeekRow

_HEADER_CLS = "text-left text-xs font-semibold text-gray-500 px-2 py-1 border-b border-gray-200"
_CELL_CLS = "px-2 py-2 border-b border-gray-100 align-top"
_SHARE_CLS = "border border-gray-300 rounded px-2 py-1 text-sm text-gray-700 hover:bg-gray-50"
_INPUT_CLS = "border border-gray-300 rounded px-2 py-1"
_DELETE_BTN_CLS = "bg-red-600 text-white rounded px-3 py-1"
_CANCEL_BTN_CLS = "border border-gray-300 rounded px-3 py-1"

_LESSON_PATH = "/realizations/lessons"
_WEEK_THEME_PATH = "/realizations/week-themes"
_DEADLINE_PATH = "/realizations/deadlines"

# The button reads its own data-share-url, so the link stays out of the inline script; the label confirms the copy.
_SHARE_JS = (
    "navigator.clipboard.writeText(this.dataset.shareUrl); this.textContent = 'Copied';"
    " setTimeout(() => { this.textContent = 'Share' }, 1500)"
)


def lesson_path(lesson_id: int) -> str:
    """The path of one Lesson's edit route, per ./realizations.sdd."""
    return f"{_LESSON_PATH}/{lesson_id}"


def lesson_delete_path(lesson_id: int) -> str:
    """The path of one Lesson's delete route, per ./realizations.sdd."""
    return f"{lesson_path(lesson_id)}/delete"


def week_theme_path(week_theme_id: int) -> str:
    """The path of one WeekTheme's edit route, per ./realizations.sdd."""
    return f"{_WEEK_THEME_PATH}/{week_theme_id}"


def week_theme_delete_path(week_theme_id: int) -> str:
    """The path of one WeekTheme's delete route, per ./realizations.sdd."""
    return f"{week_theme_path(week_theme_id)}/delete"


def week_theme_dialog_id(week: WeekRow) -> str:
    """The id of one week's WeekTheme dialog, which the week's `Week` cell opens, per ./realizations.sdd."""
    return f"week-theme-dialog-{week.start.isoformat()}"


def week_theme_delete_dialog_id(week: WeekRow) -> str:
    """The id of one week's WeekTheme delete confirmation, per ./realizations.sdd."""
    return f"week-theme-delete-dialog-{week.start.isoformat()}"


def deadline_path(deadline_id: int) -> str:
    """The path of one Deadline's edit route, per ./realizations.sdd."""
    return f"{_DEADLINE_PATH}/{deadline_id}"


def deadline_delete_path(deadline_id: int) -> str:
    """The path of one Deadline's delete route, per ./realizations.sdd."""
    return f"{deadline_path(deadline_id)}/delete"


def deadline_dialog_id(week: WeekRow) -> str:
    """The id of one week's Deadline add dialog, which that week's `Deadline` cell opens, per ./realizations.sdd."""
    return f"deadline-dialog-{week.start.isoformat()}"


def realization_selector(options: list[tuple[int, str]], selected_id: int):
    return layout.dropdown(
        "realization_id",
        options,
        selected_id,
        "/realizations",
        hx_include=f"#{layout.SEMESTER_SELECT_ID}",
    )


def no_semester_state():
    return P("No Semester has been created yet.", cls="p-4 text-sm text-gray-500")


def empty_state():
    return P("No CourseRealizations in the active Semester yet.", cls="p-4 text-sm text-gray-500")


def share_button(share_url: str):
    """A button copying the canonical shareable URL of the shown realization, per ./realizations.sdd."""
    return Button(
        "Share",
        type="button",
        onclick=_SHARE_JS,
        **{"data-share-url": share_url},
        cls=_SHARE_CLS,
    )


def realization_view(vm: RealizationViewModel, is_admin: bool = False, share_url: str = "", error: str = ""):
    """The realization's label, its Share button, a validation message and the weekly table.

    The label and the Share button sit outside the weekly table so a dialog write, which swaps only
    #realization-week-table, leaves them in place.
    """
    header = Div(
        Div(vm.label, cls="font-semibold text-lg"),
        share_button(share_url) if share_url else "",
        cls="flex items-center justify-between gap-4 px-4 pt-3 pb-2",
    )
    message = P(error, cls="px-4 pb-1 text-red-600 text-sm") if error else ""
    table = week_table(vm, is_admin)
    if not is_admin:
        return Div(header, message, table, cls="flex flex-col h-full min-h-0")
    return Div(
        header, message, table, day_dialog_view.dialog_container(), cls="flex flex-col h-full min-h-0"
    )


def week_table(vm: RealizationViewModel, is_admin: bool = False):
    """The bare weekly table, the swap target of the dialog's write responses, per ./realizations.sdd.

    The per-Lesson, per-week theme and per-Deadline dialogs live inside it so a swap from
    ../day_dialog/day_dialog.sdd's dialog, which returns the bare table, keeps every control and its dialog.
    """
    lessons = [entry for week in vm.weeks for entry in week.entries if entry.lesson_id] if is_admin else []
    deadlines = [entry for week in vm.weeks for entry in week.deadlines] if is_admin else []
    return Div(
        Table(
            Thead(
                Tr(
                    Th("Week", cls=_HEADER_CLS),
                    Th("Lessons", cls=_HEADER_CLS),
                    Th("Deadline", cls=_HEADER_CLS),
                )
            ),
            Tbody(*[row for week in vm.weeks for row in _week_rows(week, vm.realization, is_admin)]),
            cls="w-full border-collapse",
        ),
        *[
            dialog
            for entry in lessons
            for dialog in (_lesson_edit_dialog(entry), _lesson_delete_dialog(entry))
        ],
        *[
            dialog
            for week in vm.weeks
            if is_admin
            for dialog in (
                _week_theme_dialog(week, vm.realization),
                _week_theme_delete_dialog(week),
                _deadline_dialog(week, vm.realization),
            )
        ],
        *[
            dialog
            for entry in deadlines
            for dialog in (_deadline_edit_dialog(entry), _deadline_delete_dialog(entry))
        ],
        id=day_dialog_view.WEEK_TABLE_ID,
        cls="h-full w-full overflow-y-auto px-4 pb-4 max-w-5xl mx-auto",
    )


def _week_rows(week: WeekRow, realization, is_admin: bool):
    """One sub-row per entry, plus, for the admin, the week's empty Lesson add slot, per ./realizations.sdd.

    The `Week` and `Deadline` cells span every sub-row of their week (`rowspan`), including the add slot, so the
    week still reads as one row. A NoTeachWeek consumes its whole week and takes no add slot, since no Lesson is ever
    added inside it, and a visitor's empty week keeps its placeholder sub-row.
    """
    entries: list[WeekEntry | None] = list(week.entries)
    is_no_teach_week = any(entry.is_no_teach_week for entry in entries)
    show_add_slot = is_admin and not is_no_teach_week
    if not entries and not show_add_slot:
        entries = [None]
    rows: list[WeekEntry | None] = entries + ([None] if show_add_slot else [])
    rowspan = len(rows)
    return [
        Tr(
            *([_week_cell(week, is_admin, rowspan)] if i == 0 else []),
            (
                _add_lesson_cell(week, realization)
                if show_add_slot and i == len(entries)
                else _lessons_cell(entry, is_admin)
            ),
            # The Deadline cell spans the whole week, so it is rendered on the first sub-row only and spans the rest,
            # like the Week cell.
            *([_deadlines_cell(week, realization, is_admin, rowspan)] if i == 0 else []),
            **_week_row_attrs(week, is_admin),
        )
        for i, entry in enumerate(rows)
    ]


def _week_row_attrs(week: WeekRow, is_admin: bool):
    """The tint of a week blocked by a NoTeachWeek, per ./realizations.sdd.

    A NoTeachWeek consumes its whole week, so the row is tinted the mild red of ../semester/semester.sdd's wall
    planner's blocked day rows for a visitor and the admin alike; the admin's hover deepens that red instead of
    turning gray, so the week stays visibly blocked while the pointer is on it. The week row itself carries no
    trigger: the admin's affordances are the `Week` cell, the `Lessons` add slot and the `Deadline` cell.
    """
    is_no_teach_week = any(entry.is_no_teach_week for entry in week.entries)
    if not is_admin:
        return {"cls": "bg-red-50"} if is_no_teach_week else {}
    return {"cls": "bg-red-50 hover:bg-red-100"} if is_no_teach_week else {}


def _week_cell(week: WeekRow, is_admin: bool, rowspan: int):
    """One week's number and its theme on one line, its date range below, per ./realizations.sdd.

    For the admin the cell is the trigger opening that week's WeekTheme dialog, which sits beside the table.
    """
    date_range = f"{dates.format_date(week.start)} \u2013 {dates.format_date(week.end)}"
    today_cls = " border-l-4 border-l-green-500" if week.is_current_week else ""
    head = Div(
        Div(str(week.week_number), cls="text-2xl font-bold text-gray-900 leading-none"),
        Div(week.theme, cls="text-xl text-gray-800 font-semibold") if week.theme else "",
        cls="flex items-baseline gap-2",
    )
    return Td(
        Div(
            head,
            Div(date_range, cls="text-xs text-gray-500 whitespace-nowrap"),
            # That week's theme dialogs sit beside the table, so their clicks never reach this cell's trigger.
            onclick=_open_dialog(week_theme_dialog_id(week)),
            cls="cursor-pointer",
        )
        if is_admin
        else Div(head, Div(date_range, cls="text-xs text-gray-500 whitespace-nowrap")),
        rowspan=rowspan,
        cls=f"{_CELL_CLS} border-b-gray-200 pr-4{today_cls}",
    )


def _lessons_cell(entry: WeekEntry | None, is_admin: bool = False):
    if entry is None:
        return Td("\u2014", cls=f"{_CELL_CLS} text-gray-300")
    if entry.is_no_teach_week:
        # A NoTeachWeek's own title already says which break it is, per ../realizations.sdd.
        return Td(entry.title, cls=f"{_CELL_CLS} text-red-600 italic")
    if entry.is_holiday:
        # A Holiday is laid out like a Lesson, in red: its title over the day it falls on and no time range.
        return Td(
            Div(entry.title, cls="text-red-600 italic"),
            Div(_entry_day(entry), cls="text-xs text-red-400 italic"),
            cls=_CELL_CLS,
        )
    if entry.is_conference:
        # A ../conferences/conferences.sdd Conference is laid out the same way, in purple: it is the one dated entry
        # that does not block teaching, so it never reads as the red of a blocked day.
        return Td(
            Div(entry.title, cls="text-purple-600 italic"),
            Div(_entry_day(entry), cls="text-xs text-purple-400 italic"),
            cls=_CELL_CLS,
        )
    # A Lesson sub-row is the admin's edit trigger, and its free-text note reads under its day and time line, per
    # ./realizations.sdd.
    return Td(
        Div(
            Div(entry.title, cls="text-gray-900"),
            Div(_lesson_when(entry), cls="text-xs text-gray-500"),
            Div(entry.notes, cls="text-sm text-gray-600") if entry.notes else "",
            onclick=_open_dialog(f"lesson-edit-dialog-{entry.lesson_id}") if is_admin else "",
            cls="cursor-pointer" if is_admin else "",
        ),
        cls=_CELL_CLS,
    )


def _add_lesson_cell(week: WeekRow, realization):
    """The admin's empty add slot at the bottom of a week's `Lessons` column, per ./realizations.sdd.

    Clicking it opens ../day_dialog/day_dialog.sdd's add-Lesson form for that week, defaulting to the week's Monday
    and to the shown realization; the form's day calendar lets the admin pick the actual day.
    """
    return Td(
        hx_get=(
            f"{day_dialog_view.DIALOG_PATH}?semester_id={realization.semester_id}"
            f"&day={week.start.isoformat()}&kind=lesson&realization_id={realization.id}"
        ),
        hx_target=f"#{day_dialog_view.CONTAINER_ID}",
        hx_swap="innerHTML",
        cls=f"{_CELL_CLS} cursor-pointer hover:bg-gray-100",
    )


def _entry_day(entry: WeekEntry) -> str:
    """One Lesson's or Holiday's weekday and `d.m.` day, per ./realizations.sdd.

    The week row's `Week` cell already carries the week's full date range, so the sub-row repeats only the
    weekday and the `d.m.` day.
    """
    day = entry.entry_date
    return f"{day.strftime('%a')} {day.day}.{day.month}."


def _lesson_when(entry: WeekEntry) -> str:
    """One Lesson's day over its time range, per ./realizations.sdd."""
    return f"{_entry_day(entry)} {entry.start_time}\u2013{entry.end_time}"


def _deadlines_cell(week: WeekRow, realization, is_admin: bool, rowspan: int):
    """One week's `Deadline` cell, per ./realizations.sdd.

    The cell lists the week's ../deadlines/deadlines.sdd Deadlines by title over their `d.m.yyyy` date and stays
    blank when the week has none. For the admin the cell itself is the trigger opening that week's add dialog; the
    per-Deadline controls inside it stop their own clicks so they do not open that add dialog behind their own.
    """
    return Td(
        Div(*[_deadline_entry(entry, is_admin) for entry in week.deadlines]),
        rowspan=rowspan,
        onclick=_open_dialog(deadline_dialog_id(week)) if is_admin else "",
        cls=f"{_CELL_CLS} w-48" + (" cursor-pointer" if is_admin else ""),
    )


def _deadline_entry(entry: DeadlineEntry, is_admin: bool):
    return Div(
        Div(entry.title, cls="text-gray-900"),
        Div(dates.format_date(entry.date), cls="text-xs text-gray-500"),
        _deadline_controls(entry) if is_admin else "",
        cls="mb-1 last:mb-0",
    )


def _deadline_controls(entry: DeadlineEntry):
    """The admin's per-Deadline edit and delete controls.

    Each click stops its own propagation first: the cell around them is the trigger for that week's Deadline add
    dialog, which would otherwise open behind the control's own dialog.
    """
    return Div(
        A(
            "Edit",
            href="#",
            onclick=_open_dialog(f"deadline-edit-dialog-{entry.id}", stop_propagation=True),
            cls="text-xs text-blue-700 hover:text-blue-900",
        ),
        A(
            "Delete",
            href="#",
            onclick=_open_dialog(f"deadline-delete-dialog-{entry.id}", stop_propagation=True),
            cls="text-xs text-red-700 hover:text-red-900",
        ),
        cls="flex items-center gap-2 mt-1",
    )


def _open_dialog(dialog_id: str, stop_propagation: bool = False, close_id: str = "") -> str:
    """Opens a dialog, optionally closing the one it was opened from first so a confirm step replaces its opener."""
    stop = "event.stopPropagation(); " if stop_propagation else ""
    close = f"document.getElementById('{close_id}').close(); " if close_id else ""
    return (
        f"{stop}{close}var d = document.getElementById('{dialog_id}');"
        " if (d.open) d.close(); d.showModal();"
    )


def _lesson_edit_dialog(entry: WeekEntry):
    """One Lesson's edit form, prefilled with its date, times, topic and notes.

    Its `Delete` control closes the edit dialog and opens the delete confirmation, so a Lesson is removed from the
    same dialog it is edited in, per ./realizations.sdd.
    """
    return Dialog(
        Form(
            Span("Date", cls="text-xs font-semibold text-gray-500"),
            layout.day_calendar(entry.entry_date),
            Div(
                Div(
                    Span("Start time", cls="text-xs font-semibold text-gray-500"),
                    day_dialog_view.time_select(
                        "start_time", entry.start_time, day_dialog_view.START_TIME_LATEST
                    ),
                    cls="flex flex-col gap-1 flex-1",
                ),
                Div(
                    Span("End time", cls="text-xs font-semibold text-gray-500"),
                    day_dialog_view.time_select(
                        "end_time", entry.end_time, day_dialog_view.END_TIME_LATEST
                    ),
                    cls="flex flex-col gap-1 flex-1",
                ),
                cls="flex gap-2",
            ),
            Input(name="topic", value=entry.title, required=True, cls=_INPUT_CLS),
            Input(name="notes", value=entry.notes, cls=_INPUT_CLS),
            Div(
                Button("Save", type="submit", cls="bg-blue-600 text-white rounded px-3 py-1"),
                A(
                    "Delete",
                    href="#",
                    onclick=_open_dialog(
                        f"lesson-delete-dialog-{entry.lesson_id}",
                        close_id=f"lesson-edit-dialog-{entry.lesson_id}",
                    ),
                    cls="text-xs text-red-700 hover:text-red-900 self-center",
                ),
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls=_CANCEL_BTN_CLS,
                ),
                cls="flex items-center gap-2 mt-3",
            ),
            method="post",
            action=lesson_path(entry.lesson_id),
            cls="flex flex-col gap-1",
        ),
        id=f"lesson-edit-dialog-{entry.lesson_id}",
        cls="rounded p-4 w-96",
    )


def _lesson_delete_dialog(entry: WeekEntry):
    """The confirmation before one Lesson is removed, naming the Lesson and its date."""
    return Dialog(
        Div(
            f"Delete the Lesson {entry.title} on {dates.format_date(entry.entry_date)}?",
            cls="font-semibold text-sm mb-2",
        ),
        Form(
            Div(
                Button("Delete", type="submit", cls=_DELETE_BTN_CLS),
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls=_CANCEL_BTN_CLS,
                ),
                cls="flex gap-2 justify-end",
            ),
            method="post",
            action=lesson_delete_path(entry.lesson_id),
        ),
        id=f"lesson-delete-dialog-{entry.lesson_id}",
        cls="rounded p-4 w-96",
    )


def _week_theme_dialog(week: WeekRow, realization):
    """One week's WeekTheme form: the add form when the week has no theme, the edit form when it has one.

    The admin edits the title only: the week is the one whose `Week` cell opened this dialog, so its Monday is a
    hidden field, and the add form names the shown realization as a hidden field too.
    """
    date_range = f"{dates.format_date(week.start)} \u2013 {dates.format_date(week.end)}"
    return Dialog(
        Div(f"Theme of week {week.week_number}, {date_range}", cls="font-semibold text-sm mb-2"),
        Form(
            Input(name="title", value=week.theme, required=True, cls=_INPUT_CLS),
            Input(name="week_start", type="hidden", value=week.start.isoformat()),
            *(
                [Input(name="realization_id", type="hidden", value=realization.id)]
                if week.theme_id is None
                else []
            ),
            Div(
                Button("Save", type="submit", cls="bg-blue-600 text-white rounded px-3 py-1"),
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls=_CANCEL_BTN_CLS,
                ),
                *(
                    [
                        A(
                            "Delete",
                            href="#",
                            onclick=_open_dialog(
                                week_theme_delete_dialog_id(week), stop_propagation=True
                            ),
                            cls="text-xs text-red-700 hover:text-red-900 self-center",
                        )
                    ]
                    if week.theme_id is not None
                    else []
                ),
                cls="flex items-center gap-2 mt-3",
            ),
            method="post",
            action=_WEEK_THEME_PATH if week.theme_id is None else week_theme_path(week.theme_id),
            cls="flex flex-col gap-1",
        ),
        id=week_theme_dialog_id(week),
        cls="rounded p-4 w-96",
    )


def _week_theme_delete_dialog(week: WeekRow):
    """The confirmation before one week's theme is removed; empty for an unthemed week."""
    if week.theme_id is None:
        return ""
    return Dialog(
        Div(
            f"Delete the week {week.week_number} theme {week.theme}?",
            cls="font-semibold text-sm mb-2",
        ),
        Form(
            Div(
                Button("Delete", type="submit", cls=_DELETE_BTN_CLS),
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls=_CANCEL_BTN_CLS,
                ),
                cls="flex gap-2 justify-end",
            ),
            method="post",
            action=week_theme_delete_path(week.theme_id),
        ),
        id=week_theme_delete_dialog_id(week),
        cls="rounded p-4 w-96",
    )


def _deadline_dialog(week: WeekRow, realization):
    """One week's Deadline add form, opened from that week row's `Deadline` cell, per ./realizations.sdd.

    The add dialog adds only within its own week: its date field is ../shared/shared.sdd's @day_calendar over that
    week's Monday and the shown realization is a hidden field, since the cell that opened it names both.
    """
    date_range = f"{dates.format_date(week.start)} \u2013 {dates.format_date(week.end)}"
    return Dialog(
        Div(f"Add a Deadline in week {week.week_number}, {date_range}", cls="font-semibold text-sm mb-2"),
        Form(
            Span("Date", cls="text-xs font-semibold text-gray-500"),
            layout.day_calendar(week.start),
            Input(name="title", required=True, cls=_INPUT_CLS),
            Input(name="realization_id", type="hidden", value=realization.id),
            Div(
                Button("Save", type="submit", cls="bg-blue-600 text-white rounded px-3 py-1"),
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls=_CANCEL_BTN_CLS,
                ),
                cls="flex gap-2 mt-3",
            ),
            method="post",
            action=_DEADLINE_PATH,
            cls="flex flex-col gap-1",
        ),
        id=deadline_dialog_id(week),
        cls="rounded p-4 w-96",
    )


def _deadline_edit_dialog(entry: DeadlineEntry):
    """One Deadline's edit form, prefilled with its date and title.

    The Deadline stays in the realization it already belongs to, so no realization field is carried here.
    """
    return Dialog(
        Form(
            Span("Date", cls="text-xs font-semibold text-gray-500"),
            layout.day_calendar(entry.date),
            Input(name="title", value=entry.title, required=True, cls=_INPUT_CLS),
            Div(
                Button("Save", type="submit", cls="bg-blue-600 text-white rounded px-3 py-1"),
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls=_CANCEL_BTN_CLS,
                ),
                cls="flex gap-2 mt-3",
            ),
            method="post",
            action=deadline_path(entry.id),
            cls="flex flex-col gap-1",
        ),
        id=f"deadline-edit-dialog-{entry.id}",
        cls="rounded p-4 w-96",
    )


def _deadline_delete_dialog(entry: DeadlineEntry):
    """The confirmation before one Deadline is removed, naming the Deadline and its date."""
    return Dialog(
        Div(
            f"Delete the Deadline {entry.title} on {dates.format_date(entry.date)}?",
            cls="font-semibold text-sm mb-2",
        ),
        Form(
            Div(
                Button("Delete", type="submit", cls=_DELETE_BTN_CLS),
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls=_CANCEL_BTN_CLS,
                ),
                cls="flex gap-2 justify-end",
            ),
            method="post",
            action=deadline_delete_path(entry.id),
        ),
        id=f"deadline-delete-dialog-{entry.id}",
        cls="rounded p-4 w-96",
    )
