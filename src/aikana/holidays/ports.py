"""@HolidayRepository Protocol backing ./services.py, per ../architecture.sdd."""

from datetime import date
from typing import Protocol

from .domain import Holiday


class HolidayRepository(Protocol):
    def list_for_range(self, start: date, end: date) -> list[Holiday]: ...
    def add(self, holiday_date: date, title: str) -> Holiday: ...
