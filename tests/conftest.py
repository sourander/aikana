"""Shared fixtures: an in-process client and every feature's services on a temporary database, per ./tests.sdd."""

from types import SimpleNamespace

import pytest
from starlette.testclient import TestClient

from aikana.courses.repository_sqlite import SqliteCourseRepository
from aikana.courses.services import CourseService
from aikana.holidays.repository_sqlite import SqliteHolidayRepository
from aikana.holidays.services import HolidayService
from aikana.lessons.repository_sqlite import SqliteLessonRepository
from aikana.lessons.services import LessonService
from aikana.main import create_app
from aikana.no_teach_weeks.repository_sqlite import SqliteNoTeachWeekRepository
from aikana.no_teach_weeks.services import NoTeachWeekService
from aikana.realizations.repository_sqlite import SqliteCourseRealizationRepository
from aikana.realizations.services import RealizationService
from aikana.semester.repository_sqlite import SqliteSemesterRepository
from aikana.semester.services import SemesterService
from aikana.shared.db import create_database

AIKANA_PASSWD = "test-password"


@pytest.fixture
def db(tmp_path):
    return create_database(tmp_path / "app.db")


@pytest.fixture
def client(db, tmp_path, monkeypatch):
    # FastHTML writes a session key file into the working directory on app construction.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AIKANA_PASSWD", AIKANA_PASSWD)
    # Production serves HTTPS, so the in-process client runs over TLS too: the session cookie is `Secure`
    # and would not be sent over plain HTTP.
    return TestClient(create_app(db), base_url="https://testserver")


@pytest.fixture
def admin_client(client):
    client.post("/login", data={"password": AIKANA_PASSWD}, follow_redirects=True)
    return client


@pytest.fixture
def course_service(db):
    """Reads the same temporary database the app was built on, to look up Course ids."""
    return CourseService(SqliteCourseRepository(db))


@pytest.fixture
def services(db):
    """Every feature's service, wired on a temporary database the way main.py's composition root does it."""
    course_service = CourseService(SqliteCourseRepository(db))
    holiday_service = HolidayService(SqliteHolidayRepository(db))
    semester_repo = SqliteSemesterRepository(db)
    no_teach_week_service = NoTeachWeekService(SqliteNoTeachWeekRepository(db), semester_repo)
    realization_repo = SqliteCourseRealizationRepository(db)
    lesson_service = LessonService(SqliteLessonRepository(db), realization_repo, no_teach_week_service)
    realization_service = RealizationService(
        realization_repo, course_service, lesson_service, holiday_service, no_teach_week_service
    )
    semester_service = SemesterService(
        semester_repo, course_service, holiday_service, lesson_service, realization_service, no_teach_week_service
    )
    realization_service.semester_service = semester_service
    return SimpleNamespace(
        courses=course_service,
        holidays=holiday_service,
        lessons=lesson_service,
        no_teach_weeks=no_teach_week_service,
        realizations=realization_service,
        semesters=semester_service,
    )
