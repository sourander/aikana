from dataclasses import dataclass
from datetime import date, timedelta

DEFAULT_TITLE = "No teaching week"

# A fall Semester blocks weeks 42 and 51, a spring Semester weeks 1, 10 and 22, per ./no_teach_weeks.sdd.
DEFAULT_WEEK_NUMBERS: dict[str, tuple[int, ...]] = {"fall": (42, 51), "spring": (1, 10, 22)}

# Each default week carries its own Finnish break title, so the title is derived from the week number alone.
DEFAULT_WEEK_TITLES: dict[int, str] = {
    1: "Tammivapaat",
    10: "Talvivapaat",
    22: "Kesävapaat",
    42: "Syysvapaat",
    51: "Jouluvapaat",
}

# Monday through Friday; Saturday and Sunday already carry no lessons and are never blocked.
_TEACHING_WEEKDAY_OFFSETS = range(5)


@dataclass(frozen=True)
class NoTeachWeek:
    id: int
    semester_id: int
    week_number: int
    week_start: date
    title: str


def default_week_numbers(term: str) -> tuple[int, ...]:
    """The week numbers a term starts with, empty for an unknown term."""
    return DEFAULT_WEEK_NUMBERS.get(term, ())


def default_title_for_week(week_number: int) -> str:
    """The break title a default NoTeachWeek in `week_number` carries, falling back to the generic default title."""
    return DEFAULT_WEEK_TITLES.get(week_number, DEFAULT_TITLE)


def week_monday(year: int, week_number: int) -> date:
    """The Monday starting ISO `week_number` of `year`; raises `ValueError` when that year has no such week."""
    return date.fromisocalendar(year, week_number, 1)


def week_sunday(week_start: date) -> date:
    return week_start + timedelta(days=6)


def teaching_days(week_start: date) -> tuple[date, ...]:
    """The Monday-to-Friday dates of the week starting at `week_start`, in order."""
    return tuple(week_start + timedelta(days=offset) for offset in _TEACHING_WEEKDAY_OFFSETS)
