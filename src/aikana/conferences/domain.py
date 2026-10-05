"""The Conference entity, per ./conferences.sdd."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Conference:
    id: int
    date: date
    title: str