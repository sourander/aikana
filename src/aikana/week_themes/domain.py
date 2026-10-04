"""The WeekTheme entity, per ./week_themes.sdd."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class WeekTheme:
    id: int
    course_realization_id: int
    week_start: date
    title: str


def is_week_start(day: date) -> bool:
    """Whether `day` is a Monday, the only weekday that can start a week, per ./week_themes.sdd."""
    return day.isoweekday() == 1