"""The Deadline entity, per ./deadlines.sdd."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Deadline:
    id: int
    course_realization_id: int
    date: date
    title: str