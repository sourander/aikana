from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Holiday:
    id: str
    date: date
    title: str
