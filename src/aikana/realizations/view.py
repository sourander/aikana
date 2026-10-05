"""Pure rendering of the per-CourseRealization weekly view: the view's own bar (the realization selector and the
Share button) above one stacked card per calendar week, per ./realizations.sdd.

Each week card has three sections: the week head on the left (week number, optional theme, date range and the week's
Holiday and Conference flags), the Lessons in the middle and the Deadlines on the right. For the admin, clicking the
week head opens the WeekTheme dialog, clicking empty space in the Lessons section opens the add-Lesson dialog, clicking
a Lesson opens its edit dialog, and the Deadlines section behaves the same way for Deadlines.
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
)

from ..day_dialog import view as day_dialog_view
from ..shared import dates, layout
from .services import DeadlineEntry, RealizationViewModel, WeekEntry, WeekRow

_LESSON_PATH = "/realizations/lessons"
_WEEK_THEME_PATH = "/realizations/week-themes"
_DEADLINE_PATH = "/realizations/deadlines"

_VIEW_ID = "realization-view"

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
    """The id of one week's WeekTheme dialog, which the week's head opens, per ./realizations.sdd."""
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
    """The id of one week's Deadline add dialog, which that week's Deadlines section opens, per ./realizations.sdd."""
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
    return P("No Semester has been created yet.", cls="notice")


def empty_state():
    return P("No CourseRealizations in the active Semester yet.", cls="notice")


def share_button(share_url: str):
    """A button copying the canonical shareable URL of the shown realization, per ./realizations.sdd."""
    return Button(
        "Share",
        type="button",
        onclick=_SHARE_JS,
        **{"data-share-url": share_url},
        cls="btn btn--plain",
    )


def realization_view(
    vm: RealizationViewModel,
    options: list[tuple[int, str]] = (),
    selected_id: int | None = None,
    is_admin: bool = False,
    share_url: str = "",
    error: str = "",
):
    """The view's own bar (the realization selector and the Share button), a validation message and the week cards.

    The bar sits outside the week cards' swap target, so a dialog write, which swaps only #realization-week-table,
    leaves it in place.
    """
    bar = Div(
        realization_selector(options, selected_id) if options else "",
        share_button(share_url) if share_url else "",
        cls="view-bar",
    )
    message = P(error, cls="error") if error else ""
    cards = week_cards(vm, is_admin)
    if not is_admin:
        return Div(bar, message, cards, id=_VIEW_ID, cls="realization-view")
    return Div(bar, message, cards, day_dialog_view.dialog_container(), id=_VIEW_ID, cls="realization-view")


def week_cards(vm: RealizationViewModel, is_admin: bool = False):
    """The bare stack of week cards, the swap target of the dialog's write responses, per ./realizations.sdd.

    The per-Lesson, per-week theme and per-Deadline dialogs live inside it so a swap from
    ../day_dialog/day_dialog.sdd's dialog, which returns the bare cards, keeps every control and its dialog.
    """
    lessons = [entry for week in vm.weeks for entry in week.entries if entry.lesson_id] if is_admin else []
    deadlines = [entry for week in vm.weeks for entry in week.deadlines] if is_admin else []
    return Div(
        *[_week_card(week, vm.realization, is_admin) for week in vm.weeks],
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
        cls="weeks",
        # The container scrolls, so it clips any tooltip that overflows its edge; marking it the tooltip area makes
        # ../shared/layout.py's script clamp a week head's Holiday or Conference flag tooltip inside it instead.
        **{"data-tip-area": ""},
    )


def _week_card(week: WeekRow, realization, is_admin: bool):
    """One week's card: the week head, the Lessons section and the Deadlines section side by side.

    A NoTeachWeek consumes its whole week, so the card carries the blocked tint and its Lessons section reads the
    NoTeachWeek's title instead of offering Lessons, per ./realizations.sdd; the week can still carry a theme and
    Deadlines, since a deadline is an obligation rather than teaching.
    """
    entries = week.entries
    no_teach = next((entry for entry in entries if entry.is_no_teach_week), None)
    lessons = [entry for entry in entries if entry.lesson_id]
    holidays = [entry for entry in entries if entry.is_holiday]
    conferences = [entry for entry in entries if entry.is_conference]
    cls = "week-card"
    if no_teach is not None:
        cls += " week-card--blocked"
    if week.is_current_week:
        cls += " week-card--current"
    return Div(
        _week_head(week, holidays, conferences, is_admin),
        _week_lessons(week, lessons, no_teach, realization, is_admin),
        _week_deadlines(week, realization, is_admin),
        cls=cls,
    )


def _week_head(week: WeekRow, holidays: list[WeekEntry], conferences: list[WeekEntry], is_admin: bool):
    """The week's number and its theme on one line, its date range below, then the week's Holiday and Conference
    flags, per ./realizations.sdd.

    For the admin the head is the trigger opening that week's WeekTheme dialog, which sits beside the cards.
    """
    date_range = f"{dates.format_date(week.start)} \u2013 {dates.format_date(week.end)}"
    return Div(
        Div(
            Span(str(week.week_number), cls="week-num"),
            Span(week.theme, cls="week-theme") if week.theme else "",
            cls="week-headline",
        ),
        Div(date_range, cls="week-dates"),
        Div(
            *[_flag(entry, "flag--holiday") for entry in holidays],
            *[_flag(entry, "flag--conference") for entry in conferences],
            cls="week-flags",
        )
        if holidays or conferences
        else "",
        onclick=_open_dialog(week_theme_dialog_id(week)) if is_admin else None,
        cls="week-head week-head--clickable" if is_admin else "week-head",
    )


def _flag(entry: WeekEntry, modifier: str):
    """One Holiday or Conference as a small colored square whose hover tooltip names it and its day."""
    return Span(
        Div(
            Div(entry.title, cls="tip-title"),
            Div(_entry_day(entry), cls="tip-sub"),
            **{"data-tip-body": ""},
        ),
        cls=f"flag {modifier}",
        **{"data-tip": ""},
    )


def _week_lessons(week: WeekRow, lessons: list[WeekEntry], no_teach: WeekEntry | None, realization, is_admin: bool):
    """The card's middle section: the week's Lessons stacked, or the NoTeachWeek's title in red.

    For the admin the section itself is the add trigger: clicking empty space opens
    ../day_dialog/day_dialog.sdd's add-Lesson form for that week, defaulting to the week's Monday and to the shown
    realization; a Lesson's own click stops propagation first and opens its edit dialog instead. A NoTeachWeek takes
    no add trigger, since no Lesson is ever added inside it.
    """
    cls = "week-lessons"
    attrs = {}
    if is_admin and no_teach is None:
        cls += " week-lessons--clickable"
        attrs = {
            "hx_get": (
                f"{day_dialog_view.DIALOG_PATH}?semester_id={realization.semester_id}"
                f"&day={week.start.isoformat()}&kind=lesson&realization_id={realization.id}"
            ),
            "hx_target": f"#{day_dialog_view.CONTAINER_ID}",
            "hx_swap": "innerHTML",
        }
    return Div(
        *[_lesson_item(entry, is_admin) for entry in lessons],
        P(no_teach.title, cls="week-note") if no_teach is not None else "",
        cls=cls,
        **attrs,
    )


def _lesson_item(entry: WeekEntry, is_admin: bool):
    """One Lesson: its topic, under it one line with the day and time range, and its note under that, per
    ./realizations.sdd. For the admin the item is the trigger opening the Lesson's edit dialog."""
    return Div(
        Div(entry.title, cls="lesson-topic"),
        Div(_lesson_when(entry), cls="lesson-when"),
        Div(entry.notes, cls="lesson-notes") if entry.notes else "",
        onclick=_open_dialog(f"lesson-edit-dialog-{entry.lesson_id}", stop_propagation=True) if is_admin else None,
        cls="lesson lesson--clickable" if is_admin else "lesson",
    )


def _week_deadlines(week: WeekRow, realization, is_admin: bool):
    """The card's right section: the week's Deadlines stacked, by title over their `d.m.yyyy` date.

    For the admin the section itself is the add trigger opening that week's Deadline dialog, and a Deadline's own
    click stops propagation first and opens its edit dialog instead.
    """
    return Div(
        *[_deadline_item(entry, is_admin) for entry in week.deadlines],
        onclick=_open_dialog(deadline_dialog_id(week)) if is_admin else None,
        cls="week-deadlines week-deadlines--clickable" if is_admin else "week-deadlines",
    )


def _deadline_item(entry: DeadlineEntry, is_admin: bool):
    return Div(
        Div(entry.title, cls="deadline-title"),
        Div(dates.format_date(entry.date), cls="deadline-date"),
        onclick=_open_dialog(f"deadline-edit-dialog-{entry.id}", stop_propagation=True) if is_admin else None,
        cls="deadline deadline--clickable" if is_admin else "deadline",
    )


def _entry_day(entry: WeekEntry) -> str:
    """One entry's weekday and `d.m.` day, per ./realizations.sdd.

    The week head already carries the week's full date range, so the entry repeats only the weekday and the
    `d.m.` day.
    """
    day = entry.entry_date
    return f"{day.strftime('%a')} {day.day}.{day.month}."


def _lesson_when(entry: WeekEntry) -> str:
    """One Lesson's day over its time range, per ./realizations.sdd."""
    return f"{_entry_day(entry)} {entry.start_time}\u2013{entry.end_time}"


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
            Span("Date", cls="label"),
            layout.day_calendar(entry.entry_date),
            Div(
                Div(
                    Span("Start time", cls="label"),
                    day_dialog_view.time_select(
                        "start_time", entry.start_time, day_dialog_view.START_TIME_LATEST
                    ),
                    cls="form-field",
                ),
                Div(
                    Span("End time", cls="label"),
                    day_dialog_view.time_select(
                        "end_time", entry.end_time, day_dialog_view.END_TIME_LATEST
                    ),
                    cls="form-field",
                ),
                cls="form-row",
            ),
            Span("Topic", cls="label"),
            Input(name="topic", value=entry.title, required=True, cls="input"),
            Span("Notes", cls="label"),
            Input(name="notes", value=entry.notes, cls="input"),
            Div(
                Button("Save", type="submit", cls="btn"),
                A(
                    "Delete",
                    href="#",
                    onclick=_open_dialog(
                        f"lesson-delete-dialog-{entry.lesson_id}",
                        close_id=f"lesson-edit-dialog-{entry.lesson_id}",
                    ),
                    cls="link link--small link--danger",
                ),
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls="btn btn--plain",
                ),
                cls="form-actions",
            ),
            method="post",
            action=lesson_path(entry.lesson_id),
            cls="form",
        ),
        id=f"lesson-edit-dialog-{entry.lesson_id}",
    )


def _lesson_delete_dialog(entry: WeekEntry):
    """The confirmation before one Lesson is removed, naming the Lesson and its date."""
    return Dialog(
        Div(
            f"Delete the Lesson {entry.title} on {dates.format_date(entry.entry_date)}?",
            cls="dialog-title",
        ),
        Form(
            Div(
                Button("Delete", type="submit", cls="btn btn--danger"),
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls="btn btn--plain",
                ),
                cls="form-actions form-actions--end",
            ),
            method="post",
            action=lesson_delete_path(entry.lesson_id),
        ),
        id=f"lesson-delete-dialog-{entry.lesson_id}",
    )


def _week_theme_dialog(week: WeekRow, realization):
    """One week's WeekTheme form: the add form when the week has no theme, the edit form when it has one.

    The admin edits the title only: the week is the one whose head opened this dialog, so its Monday is a hidden
    field, and the add form names the shown realization as a hidden field too.
    """
    date_range = f"{dates.format_date(week.start)} \u2013 {dates.format_date(week.end)}"
    return Dialog(
        Div(f"Theme of week {week.week_number}, {date_range}", cls="dialog-title"),
        Form(
            Input(name="title", value=week.theme, required=True, cls="input"),
            Input(name="week_start", type="hidden", value=week.start.isoformat()),
            *(
                [Input(name="realization_id", type="hidden", value=realization.id)]
                if week.theme_id is None
                else []
            ),
            Div(
                Button("Save", type="submit", cls="btn"),
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls="btn btn--plain",
                ),
                *(
                    [
                        A(
                            "Delete",
                            href="#",
                            onclick=_open_dialog(
                                week_theme_delete_dialog_id(week), stop_propagation=True
                            ),
                            cls="link link--small link--danger",
                        )
                    ]
                    if week.theme_id is not None
                    else []
                ),
                cls="form-actions",
            ),
            method="post",
            action=_WEEK_THEME_PATH if week.theme_id is None else week_theme_path(week.theme_id),
            cls="form",
        ),
        id=week_theme_dialog_id(week),
    )


def _week_theme_delete_dialog(week: WeekRow):
    """The confirmation before one week's theme is removed; empty for an unthemed week."""
    if week.theme_id is None:
        return ""
    return Dialog(
        Div(
            f"Delete the week {week.week_number} theme {week.theme}?",
            cls="dialog-title",
        ),
        Form(
            Div(
                Button("Delete", type="submit", cls="btn btn--danger"),
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls="btn btn--plain",
                ),
                cls="form-actions form-actions--end",
            ),
            method="post",
            action=week_theme_delete_path(week.theme_id),
        ),
        id=week_theme_delete_dialog_id(week),
    )


def _deadline_dialog(week: WeekRow, realization):
    """One week's Deadline add form, opened from that week card's Deadlines section, per ./realizations.sdd.

    The add dialog adds only within its own week: its date field is ../shared/shared.sdd's @day_calendar over that
    week's Monday and the shown realization is a hidden field, since the section that opened it names both.
    """
    date_range = f"{dates.format_date(week.start)} \u2013 {dates.format_date(week.end)}"
    return Dialog(
        Div(f"Add a Deadline in week {week.week_number}, {date_range}", cls="dialog-title"),
        Form(
            Span("Date", cls="label"),
            layout.day_calendar(week.start),
            Span("Title", cls="label"),
            Input(name="title", required=True, cls="input"),
            Input(name="realization_id", type="hidden", value=realization.id),
            Div(
                Button("Save", type="submit", cls="btn"),
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls="btn btn--plain",
                ),
                cls="form-actions",
            ),
            method="post",
            action=_DEADLINE_PATH,
            cls="form",
        ),
        id=deadline_dialog_id(week),
    )


def _deadline_edit_dialog(entry: DeadlineEntry):
    """One Deadline's edit form, prefilled with its date and title.

    The Deadline stays in the realization it already belongs to, so no realization field is carried here. Its
    `Delete` control closes the edit dialog and opens the delete confirmation, like a Lesson's edit dialog does.
    """
    return Dialog(
        Form(
            Span("Date", cls="label"),
            layout.day_calendar(entry.date),
            Span("Title", cls="label"),
            Input(name="title", value=entry.title, required=True, cls="input"),
            Div(
                Button("Save", type="submit", cls="btn"),
                A(
                    "Delete",
                    href="#",
                    onclick=_open_dialog(
                        f"deadline-delete-dialog-{entry.id}",
                        close_id=f"deadline-edit-dialog-{entry.id}",
                    ),
                    cls="link link--small link--danger",
                ),
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls="btn btn--plain",
                ),
                cls="form-actions",
            ),
            method="post",
            action=deadline_path(entry.id),
            cls="form",
        ),
        id=f"deadline-edit-dialog-{entry.id}",
    )


def _deadline_delete_dialog(entry: DeadlineEntry):
    """The confirmation before one Deadline is removed, naming the Deadline and its date."""
    return Dialog(
        Div(
            f"Delete the Deadline {entry.title} on {dates.format_date(entry.date)}?",
            cls="dialog-title",
        ),
        Form(
            Div(
                Button("Delete", type="submit", cls="btn btn--danger"),
                Button(
                    "Cancel",
                    type="button",
                    onclick="this.closest('dialog').close()",
                    cls="btn btn--plain",
                ),
                cls="form-actions form-actions--end",
            ),
            method="post",
            action=deadline_delete_path(entry.id),
        ),
        id=f"deadline-delete-dialog-{entry.id}",
    )
