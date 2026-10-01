from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True)
class Lesson:
    id: str
    course_realization_id: str
    date: date
    start_time: time
    end_time: time
    topic: str
    notes: str
