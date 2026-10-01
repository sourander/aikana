"""Placeholder stand-in for a @CourseRealizationRepository-backed service, per ./realizations.sdd Tasks."""

from ..courses.domain import Course
from ..semester.domain import Semester
from .domain import CourseRealization

_PLACEHOLDER_REALIZATIONS = [
    CourseRealization(id="realization-1", course_id="course-1", semester_id="semester-1", group="TTV24SP"),
    CourseRealization(id="realization-2", course_id="course-2", semester_id="semester-1", group="TTV25A"),
]


def list_realizations_for_semester(semester_id: str) -> list[CourseRealization]:
    return [r for r in _PLACEHOLDER_REALIZATIONS if r.semester_id == semester_id]


def realization_label(realization: CourseRealization, course: Course, semester: Semester) -> str:
    """Composed at render time, never stored, per ./realizations.sdd Must."""
    return f"{course.name} ({realization.group}) \u2013 {semester.term.capitalize()} {semester.year}"
