"""Pure rendering of the per-CourseRealization weekly table, its realization selector and, for the admin, the
per-Lesson edit and delete controls with their dialogs, per ./realizations.sdd.
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
from .services import RealizationViewModel, WeekEntry, WeekRow

_HEADER_CLS = "text-left text-xs font-semibold text-gray-500 px-2 py-1 border-b border-gray-200"
_CELL_CLS = "px-2 py-2 border-b border-gray-100 align-top"
_SHARE_CLS = "border border-gray-300 rounded px-2 py-1 text-sm text-gray-700 hover:bg-gray-50"
_INPUT_CLS = "border border-gray-300 rounded px-2 py-1"
_DELETE_BTN_CLS = "bg-red-600 text-white rounded px-3 py-1"
_CANCEL_BTN_CLS = "border border-gray-300 rounded px-3 py-1"

_LESSON_PATH = "/realizations/lessons"

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

    The per-Lesson dialogs live inside it so a swap from ../day_dialog/day_dialog.sdd's dialog, which returns the
    bare table, keeps every control and its dialog.
    """
    lessons = [entry for week in vm.weeks for entry in week.entries if entry.lesson_id] if is_admin else []
    return Div(
        Table(
            Thead(Tr(Th("Week", cls=_HEADER_CLS), Th("Lessons", cls=_HEADER_CLS), Th("Notes", cls=_HEADER_CLS))),
            Tbody(*[row for week in vm.weeks for row in _week_rows(week, vm.realization, is_admin)]),
            cls="w-full border-collapse",
        ),
        *[
            dialog
            for entry in lessons
            for dialog in (_lesson_edit_dialog(entry), _lesson_delete_dialog(entry))
        ],
        id=day_dialog_view.WEEK_TABLE_ID,
        cls="h-full overflow-y-auto px-4 pb-4",
    )


def _week_rows(week: WeekRow, realization, is_admin: bool):
    entries: list[WeekEntry | None] = list(week.entries) or [None]
    return [
        Tr(
            *([_week_cell(week, len(entries))] if i == 0 else []),
            _lessons_cell(entry, is_admin),
            _notes_cell(entry),
            **_week_row_attrs(week, realization, is_admin),
        )
        for i, entry in enumerate(entries)
    ]


def _week_row_attrs(week: WeekRow, realization, is_admin: bool):
    """Clicking a week row opens the dialog for that week's Monday, per ./realizations.sdd."""
    if not is_admin:
        return {}
    return {
        "hx_get": (
            f"{day_dialog_view.DIALOG_PATH}?semester_id={realization.semester_id}"
            f"&day={week.start.isoformat()}&kind=lesson&realization_id={realization.id}"
        ),
        "hx_target": f"#{day_dialog_view.CONTAINER_ID}",
        "hx_swap": "innerHTML",
        "cls": "cursor-pointer hover:bg-gray-100",
    }


def _week_cell(week: WeekRow, rowspan: int):
    date_range = f"{dates.format_date(week.start)} \u2013 {dates.format_date(week.end)}"
    today_cls = " border-l-4 border-l-green-500" if week.is_current_week else ""
    return Td(
        Div(str(week.week_number), cls="text-2xl font-bold text-gray-900 leading-none"),
        Div(date_range, cls="text-xs text-gray-500 whitespace-nowrap"),
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
        return Td(f"Holiday \u2013 {entry.title}", cls=f"{_CELL_CLS} text-red-600 italic")
    return Td(
        Div(entry.title, cls="text-gray-900"),
        Div(_lesson_when(entry), cls="text-xs text-gray-500"),
        _lesson_controls(entry) if is_admin else "",
        cls=_CELL_CLS,
    )


def _lesson_when(entry: WeekEntry) -> str:
    """One Lesson's weekday, day and time range, per ./realizations.sdd.

    The week row's `Week` cell already carries the week's full date range, so the sub-row repeats only the
    weekday and the `d.m.` day.
    """
    day = entry.lesson_date
    return f"{day.strftime('%a')} {day.day}.{day.month}. {entry.start_time}\u2013{entry.end_time}"


def _notes_cell(entry: WeekEntry | None):
    text = entry.notes if entry and not (entry.is_holiday or entry.is_no_teach_week) else ""
    return Td(text, cls=f"{_CELL_CLS} text-gray-600 text-sm")


def _lesson_controls(entry: WeekEntry):
    """The admin's per-Lesson edit and delete controls.

    Each click stops its own propagation first: the surrounding week row opens ../day_dialog/day_dialog.sdd's
    dialog, which would otherwise open behind the control's own dialog.
    """
    return Div(
        A(
            "Edit",
            href="#",
            onclick=_open_dialog(f"lesson-edit-dialog-{entry.lesson_id}", stop_propagation=True),
            cls="text-xs text-blue-700 hover:text-blue-900",
        ),
        A(
            "Delete",
            href="#",
            onclick=_open_dialog(f"lesson-delete-dialog-{entry.lesson_id}", stop_propagation=True),
            cls="text-xs text-red-700 hover:text-red-900",
        ),
        cls="flex items-center gap-2 mt-1",
    )


def _open_dialog(dialog_id: str, stop_propagation: bool = False) -> str:
    """Opens a dialog, closing the one it was opened from first so a confirm step replaces its opener."""
    stop = "event.stopPropagation(); " if stop_propagation else ""
    return f"{stop}var d = document.getElementById('{dialog_id}'); if (d.open) d.close(); d.showModal();"


def _lesson_edit_dialog(entry: WeekEntry):
    """One Lesson's edit form, prefilled with its date, times, topic and notes."""
    return Dialog(
        Form(
            Span("Date", cls="text-xs font-semibold text-gray-500"),
            layout.day_calendar(entry.lesson_date),
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
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls=_CANCEL_BTN_CLS,
                ),
                cls="flex gap-2 mt-3",
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
            f"Delete the Lesson {entry.title} on {dates.format_date(entry.lesson_date)}?",
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