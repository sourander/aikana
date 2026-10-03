from dataclasses import dataclass


@dataclass(frozen=True)
class CourseRealization:
    id: int
    course_id: int
    semester_id: int
    group: str
