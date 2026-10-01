from dataclasses import dataclass


@dataclass(frozen=True)
class CourseRealization:
    id: str
    course_id: str
    semester_id: str
    group: str
