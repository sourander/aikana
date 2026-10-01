from dataclasses import dataclass


@dataclass(frozen=True)
class Course:
    id: str
    name: str
    description: str
    ects_credits: int
