"""@CourseRepository-backed use cases, per ./courses.sdd."""

from .domain import Course
from .ports import CourseRepository


class CourseService:
    def __init__(self, repo: CourseRepository) -> None:
        self.repo = repo

    def list_courses(self) -> list[Course]:
        return self.repo.list()

    def get_course(self, course_id: str) -> Course | None:
        return self.repo.get(course_id)

    def add_course(self, name: str, description: str, ects_credits: int) -> Course:
        return self.repo.add(name, description, ects_credits)

