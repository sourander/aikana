"""@CourseRepository-backed use cases, per ./courses.sdd."""

from .domain import Course
from .ports import CourseRepository


class InvalidCourseError(Exception):
    pass


class DuplicateCourseError(Exception):
    pass


class UnknownCourseError(Exception):
    pass


class CourseService:
    def __init__(self, repo: CourseRepository) -> None:
        self.repo = repo

    def list_courses(self) -> list[Course]:
        return self.repo.list()

    def get_course(self, course_id: str) -> Course | None:
        return self.repo.get(course_id)

    def add_course(self, name: str, description: str, ects_credits: int) -> Course:
        return self.repo.add(self._validated_name(name), description, ects_credits)

    def update_course(self, course_id: str, name: str, description: str, ects_credits: int) -> Course:
        if self.repo.get(course_id) is None:
            raise UnknownCourseError(f"No Course with id {course_id!r}.")
        return self.repo.update(course_id, self._validated_name(name, exclude_id=course_id), description, ects_credits)

    def _validated_name(self, name: str, exclude_id: str | None = None) -> str:
        name = name.strip()
        if not name:
            raise InvalidCourseError("A Course needs a non-empty name.")
        if any(course.id != exclude_id and course.name.lower() == name.lower() for course in self.repo.list()):
            raise DuplicateCourseError(f"A Course named {name!r} already exists.")
        return name

