"""Pure rendering of the semester wall planner (one column per month, one row per day)."""

from fasthtml.common import Div, Span

from .services import DayCell, MonthColumn, SemesterViewModel


def semester_view(vm: SemesterViewModel):
    return Div(
        *[_month_column(month) for month in vm.months],
        style=f"display:grid; grid-template-columns:repeat({len(vm.months)}, 1fr); gap:10px; "
        "height:100%; overflow:hidden;",
        cls="p-4",
    )


def _month_column(month: MonthColumn):
    return Div(
        Div(month.label, cls="font-semibold text-center border-b border-gray-300 pb-1 mb-1"),
        Div(*[_day_row(day) for day in month.days], cls="flex-1 flex flex-col min-h-0"),
        style="display:flex; flex-direction:column; min-width:0;",
    )


def _day_row(day: DayCell):
    holiday_cls = "bg-red-50" if day.holiday_title else ""
    return Div(
        Span(day.weekday_label, cls="w-8 text-xs text-gray-500 shrink-0"),
        Span(str(day.day.day), cls="w-5 text-sm shrink-0"),
        Div(*[_lesson_square(square) for square in day.squares], cls="flex-1 flex items-center gap-1 flex-wrap"),
        Span(day.holiday_title, cls="text-xs text-red-600 truncate") if day.holiday_title else "",
        cls=f"flex items-center gap-1 border-b border-gray-100 {holiday_cls}",
        style="flex:1;",
    )


def _lesson_square(square):
    time_range = f"{square.start_time.strftime('%H:%M')}\u2013{square.end_time.strftime('%H:%M')}"
    return Span(
        Div(
            Div(square.realization_label, cls="font-semibold text-gray-900"),
            Div(time_range, cls="text-gray-500"),
            Div(square.topic, cls="text-gray-800"),
            Div(square.notes, cls="text-gray-400 italic mt-1") if square.notes else "",
            cls="pointer-events-none absolute left-1/2 -translate-x-1/2 bottom-full mb-1 hidden w-56 "
            "flex-col gap-0.5 whitespace-normal break-words rounded-lg border border-gray-200 bg-white "
            "p-3 text-xs leading-snug shadow-lg group-hover:flex z-20",
        ),
        cls="group relative inline-block w-3 h-3 rounded-sm",
        style=f"background-color:{square.color};",
    )
