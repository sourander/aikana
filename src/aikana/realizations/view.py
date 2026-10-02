"""Pure rendering of the per-CourseRealization weekly table and its realization selector."""

from fasthtml.common import Button, Div, P, Table, Tbody, Td, Th, Thead, Tr

from ..day_dialog import view as day_dialog_view
from ..no_teach_weeks.domain import DEFAULT_TITLE
from ..shared import dates, layout
from .services import RealizationViewModel, WeekEntry, WeekRow

_HEADER_CLS = "text-left text-xs font-semibold text-gray-500 px-2 py-1 border-b border-gray-200"
_CELL_CLS = "px-2 py-2 border-b border-gray-100 align-top"
_SHARE_CLS = "border border-gray-300 rounded px-2 py-1 text-sm text-gray-700 hover:bg-gray-50"

# The button reads its own data-share-url, so the link stays out of the inline script; the label confirms the copy.
_SHARE_JS = (
    "navigator.clipboard.writeText(this.dataset.shareUrl); this.textContent = 'Copied';"
    " setTimeout(() => { this.textContent = 'Share' }, 1500)"
)


def realization_selector(options: list[tuple[str, str]], selected_id: str):
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


def realization_view(vm: RealizationViewModel, is_admin: bool = False, share_url: str = ""):
    """The realization's label, its Share button and the weekly table.

    The label and the Share button sit outside the weekly table so a dialog write, which swaps only
    #realization-week-table, leaves them in place.
    """
    header = Div(
        Div(vm.label, cls="font-semibold text-lg"),
        share_button(share_url) if share_url else "",
        cls="flex items-center justify-between gap-4 px-4 pt-3 pb-2",
    )
    table = week_table(vm, is_admin)
    if not is_admin:
        return Div(header, table, cls="flex flex-col h-full min-h-0")
    return Div(header, table, day_dialog_view.dialog_container(), cls="flex flex-col h-full min-h-0")


def week_table(vm: RealizationViewModel, is_admin: bool = False):
    """The bare weekly table, the swap target of the dialog's write responses, per ./realizations.sdd."""
    return Div(
        Table(
            Thead(Tr(Th("Week", cls=_HEADER_CLS), Th("Lessons", cls=_HEADER_CLS), Th("Notes", cls=_HEADER_CLS))),
            Tbody(*[row for week in vm.weeks for row in _week_rows(week, vm.realization, is_admin)]),
            cls="w-full border-collapse",
        ),
        id=day_dialog_view.WEEK_TABLE_ID,
        cls="h-full overflow-y-auto px-4 pb-4",
    )


def _week_rows(week: WeekRow, realization, is_admin: bool):
    entries: list[WeekEntry | None] = list(week.entries) or [None]
    return [
        Tr(
            *([_week_cell(week, len(entries))] if i == 0 else []),
            _lessons_cell(entry),
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
            f"&day={week.start.isoformat()}&kind=holiday&realization_id={realization.id}"
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


def _lessons_cell(entry: WeekEntry | None):
    if entry is None:
        return Td("\u2014", cls=f"{_CELL_CLS} text-gray-300")
    if entry.is_no_teach_week:
        # A NoTeachWeek's default title is already "No teaching week", so only a custom title is appended.
        label = entry.title if entry.title == DEFAULT_TITLE else f"No teaching week \u2013 {entry.title}"
        return Td(label, cls=f"{_CELL_CLS} text-red-600 italic")
    if entry.is_holiday:
        return Td(f"Holiday \u2013 {entry.title}", cls=f"{_CELL_CLS} text-red-600 italic")
    return Td(Div(entry.title, cls="text-gray-900"), Div(entry.time_range, cls="text-xs text-gray-500"), cls=_CELL_CLS)


def _notes_cell(entry: WeekEntry | None):
    text = entry.notes if entry and not (entry.is_holiday or entry.is_no_teach_week) else ""
    return Td(text, cls=f"{_CELL_CLS} text-gray-600 text-sm")
