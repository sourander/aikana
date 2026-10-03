from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Holiday:
    id: int
    date: date
    title: str
