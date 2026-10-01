from dataclasses import dataclass
from datetime import date
from typing import Literal

Term = Literal["spring", "fall"]


@dataclass(frozen=True)
class Semester:
    id: str
    year: int
    term: Term


# A fall Semester spans Aug 1 - Dec 31 of its year; a spring Semester spans Jan 1 - Jun 30, per ./semester.sdd.
def semester_bounds(semester: Semester) -> tuple[date, date]:
    if semester.term == "fall":
        return date(semester.year, 8, 1), date(semester.year, 12, 31)
    return date(semester.year, 1, 1), date(semester.year, 6, 30)


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


def default_semester(semesters: list[Semester], today: date) -> Semester | None:
    """The Semester whose period most recently started on or before `today`, else the earliest, per ./semester.sdd."""
    if not semesters:
        return None
    ordered = sorted(semesters, key=lambda semester: semester_bounds(semester)[0])
    started = [semester for semester in ordered if semester_bounds(semester)[0] <= today]
    return started[-1] if started else ordered[0]
