"""Placeholder stand-in for a @LessonRepository-backed service, per ./lessons.sdd Tasks."""

from datetime import date, time

from .domain import Lesson

_PLACEHOLDER_LESSONS = [
    Lesson(
        id="lesson-1",
        course_realization_id="realization-1",
        date=date(2026, 8, 12),
        start_time=time(10, 0),
        end_time=time(11, 30),
        topic="Course introduction & setup",
        notes="Placeholder lesson for the first visual pass.",
    ),
    Lesson(
        id="lesson-2",
        course_realization_id="realization-1",
        date=date(2026, 9, 9),
        start_time=time(10, 0),
        end_time=time(11, 30),
        topic="Supervised learning basics",
        notes="Placeholder lesson for the first visual pass.",
    ),
    Lesson(
        id="lesson-3",
        course_realization_id="realization-1",
        date=date(2026, 10, 14),
        start_time=time(10, 0),
        end_time=time(11, 30),
        topic="Neural networks",
        notes="Placeholder lesson for the first visual pass.",
    ),
    Lesson(
        id="lesson-4",
        course_realization_id="realization-1",
        date=date(2026, 11, 11),
        start_time=time(10, 0),
        end_time=time(11, 30),
        topic="Model evaluation",
        notes="Placeholder lesson for the first visual pass.",
    ),
    Lesson(
        id="lesson-5",
        course_realization_id="realization-1",
        date=date(2026, 12, 2),
        start_time=time(10, 0),
        end_time=time(11, 30),
        topic="Final project presentations",
        notes="Placeholder lesson for the first visual pass.",
    ),
    Lesson(
        id="lesson-6",
        course_realization_id="realization-2",
        date=date(2026, 8, 19),
        start_time=time(13, 0),
        end_time=time(14, 30),
        topic="HTML & CSS refresher",
        notes="Placeholder lesson for the first visual pass.",
    ),
    Lesson(
        id="lesson-7",
        course_realization_id="realization-2",
        date=date(2026, 9, 16),
        start_time=time(13, 0),
        end_time=time(14, 30),
        topic="Server-rendered apps with FastHTML",
        notes="Placeholder lesson for the first visual pass.",
    ),
    Lesson(
        id="lesson-8",
        course_realization_id="realization-2",
        date=date(2026, 10, 21),
        start_time=time(13, 0),
        end_time=time(14, 30),
        topic="HTMX interactivity",
        notes="Placeholder lesson for the first visual pass.",
    ),
    Lesson(
        id="lesson-9",
        course_realization_id="realization-2",
        date=date(2026, 11, 18),
        start_time=time(13, 0),
        end_time=time(14, 30),
        topic="Persistence with SQLite",
        notes="Placeholder lesson for the first visual pass.",
    ),
    Lesson(
        id="lesson-10",
        course_realization_id="realization-2",
        date=date(2026, 12, 2),
        start_time=time(13, 0),
        end_time=time(14, 30),
        topic="Deployment & wrap-up",
        notes="Placeholder lesson for the first visual pass.",
    ),
]


def list_lessons_for_realization(course_realization_id: str) -> list[Lesson]:
    return [lesson for lesson in _PLACEHOLDER_LESSONS if lesson.course_realization_id == course_realization_id]
