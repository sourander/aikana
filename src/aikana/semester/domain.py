from dataclasses import dataclass
from datetime import date
from typing import Literal

Term = Literal["spring", "fall"]


@dataclass(frozen=True)
class Semester:
    id: str
    year: int
    term: Term


# Hardcoded periods of academic year 2026-2027, per ./semester.sdd Must/Example.
_PERIOD_BOUNDS: dict[tuple[int, Term], tuple[date, date]] = {
    (2026, "fall"): (date(2026, 8, 1), date(2026, 12, 31)),
    (2027, "spring"): (date(2027, 1, 1), date(2027, 6, 30)),
}


def semester_bounds(semester: Semester) -> tuple[date, date]:
    return _PERIOD_BOUNDS[(semester.year, semester.term)]


def semester_months(semester: Semester) -> list[tuple[int, int]]:
    """The (year, month) pairs spanned by the semester, in order."""
    start, end = semester_bounds(semester)
    months: list[tuple[int, int]] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append((year, month))
        month += 1
        if month == 13:
            month = 1
            year += 1
    return months
