"""Pure rendering of the per-CourseRealization weekly table and its realization selector."""

from fasthtml.common import Div, P, Table, Tbody, Td, Th, Thead, Tr

from ..no_teach_weeks.domain import DEFAULT_TITLE
from ..shared import layout
from .services import RealizationViewModel, WeekEntry, WeekRow

_HEADER_CLS = "text-left text-xs font-semibold text-gray-500 px-2 py-1 border-b border-gray-200"
_CELL_CLS = "px-2 py-2 border-b border-gray-100 align-top"


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


def realization_view(vm: RealizationViewModel):
    return Div(
        Div(vm.label, cls="font-semibold text-lg px-4 pt-3 pb-2"),
        Table(
            Thead(Tr(Th("Week", cls=_HEADER_CLS), Th("Lessons", cls=_HEADER_CLS), Th("Notes", cls=_HEADER_CLS))),
            Tbody(*[row for week in vm.weeks for row in _week_rows(week)]),
            cls="w-full border-collapse",
        ),
        cls="h-full overflow-y-auto px-4 pb-4",
    )


def _week_rows(week: WeekRow):
    entries: list[WeekEntry | None] = list(week.entries) or [None]
    return [
        Tr(*([_week_cell(week, len(entries))] if i == 0 else []), _lessons_cell(entry), _notes_cell(entry))
        for i, entry in enumerate(entries)
    ]


def _week_cell(week: WeekRow, rowspan: int):
    date_range = f"{week.start.isoformat()} \u2013 {week.end.isoformat()}"
    return Td(
        Div(str(week.week_number), cls="text-2xl font-bold text-gray-900 leading-none"),
        Div(date_range, cls="text-xs text-gray-500 whitespace-nowrap"),
        rowspan=rowspan,
        cls=f"{_CELL_CLS} border-b-gray-200 pr-4",
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
