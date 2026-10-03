from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True)
class Lesson:
    id: int
    course_realization_id: int
    date: date
    start_time: time
    end_time: time
    topic: str
    notes: str
