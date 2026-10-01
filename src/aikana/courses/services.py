"""Placeholder stand-in for a @CourseRepository-backed service, per ./courses.sdd Tasks."""

from .domain import Course

_PLACEHOLDER_COURSES = [
    Course(
        id="course-1",
        name="Machine Learning",
        description="Introduction to supervised and unsupervised learning techniques.",
        ects_credits=5,
    ),
    Course(
        id="course-2",
        name="Web Programming",
        description="Building server-rendered web applications with modern tools.",
        ects_credits=5,
    ),
]


def list_courses() -> list[Course]:
    return list(_PLACEHOLDER_COURSES)


def get_course(course_id: str) -> Course:
    return next(course for course in _PLACEHOLDER_COURSES if course.id == course_id)
