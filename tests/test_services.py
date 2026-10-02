"""Service-layer validation tests against a temporary database, per ./tests.sdd."""

from datetime import date, time
from types import SimpleNamespace

import pytest

from aikana.courses.domain import Course
from aikana.courses.repository_sqlite import SqliteCourseRepository
from aikana.courses.services import (
    CourseService,
    DuplicateCourseError,
    InvalidCourseError,
    UnknownCourseError as UnknownCourseIdError,
)
from aikana.holidays.repository_sqlite import SqliteHolidayRepository
from aikana.holidays.services import HolidayService, InvalidHolidayError
from aikana.lessons.repository_sqlite import SqliteLessonRepository
from aikana.lessons.services import InvalidLessonError, LessonService, UnknownRealizationError
from aikana.realizations.repository_sqlite import SqliteCourseRealizationRepository
from aikana.realizations.services import (
    InvalidRealizationError,
    RealizationService,
    UnknownCourseError,
    UnknownSemesterError,
)
from aikana.semester.repository_sqlite import SqliteSemesterRepository
from aikana.semester.services import DuplicateSemesterError, InvalidTermError, SemesterService
from aikana.shared.db import create_database


@pytest.fixture
def services(tmp_path):
    """Every feature's service, wired on a temporary database the way main.py's composition root does it."""
    db = create_database(tmp_path / "app.db")
    course_service = CourseService(SqliteCourseRepository(db))
    holiday_service = HolidayService(SqliteHolidayRepository(db))
    realization_repo = SqliteCourseRealizationRepository(db)
    lesson_service = LessonService(SqliteLessonRepository(db), realization_repo)
    realization_service = RealizationService(realization_repo, course_service, lesson_service, holiday_service)
    semester_service = SemesterService(
        SqliteSemesterRepository(db), course_service, holiday_service, lesson_service, realization_service
    )
    realization_service.semester_service = semester_service
    return SimpleNamespace(
        courses=course_service,
        holidays=holiday_service,
        lessons=lesson_service,
        realizations=realization_service,
        semesters=semester_service,
    )


@pytest.fixture
def realization(services):
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    semester = services.semesters.create_semester(2026, "fall")
    return services.realizations.add_realization(course.id, semester.id, "TTV24SP")


# Courses


def test_add_course_rejects_an_empty_name(services):
    with pytest.raises(InvalidCourseError):
        services.courses.add_course("   ", "An introduction.", 5)


def test_add_course_rejects_a_duplicate_name_ignoring_case_and_whitespace(services):
    services.courses.add_course("Machine Learning", "An introduction.", 5)
    with pytest.raises(DuplicateCourseError):
        services.courses.add_course("  machine learning ", "Another one.", 5)


def test_update_course_rejects_an_unknown_id(services):
    with pytest.raises(UnknownCourseIdError):
        services.courses.update_course("no-such-course", "Machine Learning", "An introduction.", 5)


def test_update_course_rejects_an_empty_name(services):
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    with pytest.raises(InvalidCourseError):
        services.courses.update_course(course.id, "   ", "An introduction.", 5)


def test_update_course_rejects_a_duplicate_name_ignoring_case_and_whitespace(services):
    services.courses.add_course("Machine Learning", "An introduction.", 5)
    course = services.courses.add_course("Databases", "Another one.", 5)
    with pytest.raises(DuplicateCourseError):
        services.courses.update_course(course.id, "  machine learning ", "Another one.", 5)


def test_update_course_changes_the_stored_values(services):
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    updated = services.courses.update_course(course.id, "Deep Learning", "Advanced.", 8)
    assert updated == Course(id=course.id, name="Deep Learning", description="Advanced.", ects_credits=8)
    assert services.courses.get_course(course.id) == updated


# Semesters


def test_create_semester_rejects_a_duplicate_year_term_combination(services):
    services.semesters.create_semester(2026, "fall")
    with pytest.raises(DuplicateSemesterError):
        services.semesters.create_semester(2026, "fall")


def test_create_semester_rejects_an_invalid_term(services):
    with pytest.raises(InvalidTermError):
        services.semesters.create_semester(2026, "summer")


# CourseRealizations


def test_add_realization_rejects_an_unknown_course(services):
    semester = services.semesters.create_semester(2026, "fall")
    with pytest.raises(UnknownCourseError):
        services.realizations.add_realization("no-such-course", semester.id, "TTV24SP")


def test_add_realization_rejects_an_unknown_semester(services):
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    with pytest.raises(UnknownSemesterError):
        services.realizations.add_realization(course.id, "no-such-semester", "TTV24SP")


def test_add_realization_rejects_an_empty_group(services):
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    semester = services.semesters.create_semester(2026, "fall")
    with pytest.raises(InvalidRealizationError):
        services.realizations.add_realization(course.id, semester.id, " ")


# Lessons


def test_add_lesson_rejects_an_unknown_realization(services):
    with pytest.raises(UnknownRealizationError):
        services.lessons.add_lesson("no-such-realization", date(2026, 9, 1), time(8, 0), time(10, 0), "Intro", "")


def test_add_lesson_rejects_an_empty_topic(services, realization):
    with pytest.raises(InvalidLessonError):
        services.lessons.add_lesson(realization.id, date(2026, 9, 1), time(8, 0), time(10, 0), "", "")


def test_add_lesson_rejects_an_end_time_not_after_the_start_time(services, realization):
    with pytest.raises(InvalidLessonError):
        services.lessons.add_lesson(realization.id, date(2026, 9, 1), time(10, 0), time(10, 0), "Intro", "")


def test_add_lesson_stores_a_valid_lesson(services, realization):
    lesson = services.lessons.add_lesson(realization.id, date(2026, 9, 1), time(8, 0), time(10, 0), "Intro", "Room B")
    assert services.lessons.list_lessons_for_realization(realization.id) == [lesson]


def test_lessons_for_a_day_are_ordered_by_start_time(services, realization):
    late = services.lessons.add_lesson(realization.id, date(2026, 9, 1), time(13, 0), time(15, 0), "Late", "")
    early = services.lessons.add_lesson(realization.id, date(2026, 9, 1), time(8, 0), time(10, 0), "Early", "")
    assert services.lessons.list_lessons_for_realization(realization.id) == [early, late]


# Holidays


def test_add_holiday_rejects_an_empty_title(services):
    with pytest.raises(InvalidHolidayError):
        services.holidays.add_holiday(date(2026, 12, 6), "  ")
