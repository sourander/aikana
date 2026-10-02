from datetime import date, time
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
from aikana.shared import dates
from aikana.shared.db import create_database

AIKANA_PASSWD = "test-password"

# A date whose `today()` is fixed, so the time-dependent highlighting is testable.
FIXED_TODAY = date(2026, 10, 20)


@pytest.fixture
def db(tmp_path):
    return create_database(tmp_path / "app.db")


@pytest.fixture
def client(db, tmp_path, monkeypatch):
    # FastHTML writes a session key file into the working directory on app construction.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AIKANA_PASSWD", AIKANA_PASSWD)
    return TestClient(create_app(db))


@pytest.fixture
def services(db):
    """Seeds data on the same temporary database the app was built on, wired as main.py's composition root does."""
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


def test_index_shows_no_semester_notice_to_a_visitor(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Aikana" in response.text
    assert "No Semester has been created yet." in response.text
    assert "Create Semester" not in response.text


def test_index_shows_the_create_semester_form_to_the_admin(client):
    client.post("/login", data={"password": AIKANA_PASSWD}, follow_redirects=True)

    response = client.get("/")

    assert response.status_code == 200
    assert "Create a Semester to get started." in response.text


def test_realizations_view_renders_without_semesters(client):
    response = client.get("/realizations")

    assert response.status_code == 200
    assert "No Semester has been created yet." in response.text


def test_semester_selector_is_present_on_every_tab(client, services):
    services.semesters.create_semester(2026, "fall")
    services.semesters.create_semester(2027, "spring")

    for path in ("/", "/courses", "/realizations"):
        response = client.get(path)
        assert response.status_code == 200
        assert 'name="semester_id"' in response.text
        assert "Fall 2026" in response.text
        assert "Spring 2027" in response.text


def test_nav_links_carry_the_selected_semester(client, services):
    spring = services.semesters.create_semester(2027, "spring")

    response = client.get(f"/courses?semester_id={spring.id}")

    assert f'href="/?semester_id={spring.id}"' in response.text
    assert f'href="/courses?semester_id={spring.id}"' in response.text
    assert f'href="/realizations?semester_id={spring.id}"' in response.text
    assert f'<option value="{spring.id}" selected>' in response.text


def test_realizations_view_filters_by_the_selected_semester(client, services):
    fall = services.semesters.create_semester(2026, "fall")
    spring = services.semesters.create_semester(2027, "spring")
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    services.realizations.add_realization(course.id, fall.id, "TTV24SP")
    spring_realization = services.realizations.add_realization(course.id, spring.id, "TTV25SP")

    response = client.get(f"/realizations?semester_id={spring.id}")

    assert "TTV25SP" in response.text
    assert "TTV24SP" not in response.text
    assert f'<option value="{spring_realization.id}" selected>' in response.text


def test_realizations_view_infers_the_semester_from_a_realization(client, services):
    fall = services.semesters.create_semester(2026, "fall")
    spring = services.semesters.create_semester(2027, "spring")
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    services.realizations.add_realization(course.id, fall.id, "TTV24SP")
    spring_realization = services.realizations.add_realization(course.id, spring.id, "TTV25SP")

    response = client.get(f"/realizations?realization_id={spring_realization.id}")

    assert "TTV25SP" in response.text
    assert "TTV24SP" not in response.text
    assert f'<option value="{spring.id}" selected>' in response.text


def test_courses_page_ignores_the_selected_semester(client, services):
    fall = services.semesters.create_semester(2026, "fall")
    spring = services.semesters.create_semester(2027, "spring")
    services.courses.add_course("Machine Learning", "An introduction.", 5)

    fall_page = client.get(f"/courses?semester_id={fall.id}")
    spring_page = client.get(f"/courses?semester_id={spring.id}")

    assert "Machine Learning" in fall_page.text
    assert "Machine Learning" in spring_page.text
    assert f'<option value="{fall.id}" selected>' in fall_page.text
    assert f'<option value="{spring.id}" selected>' in spring_page.text


# NoTeachWeeks


def test_wall_planner_tints_and_titles_each_weekday_of_a_no_teach_week(client, services):
    semester = services.semesters.create_semester(2026, "fall")

    response = client.get(f"/?semester_id={semester.id}")

    assert response.status_code == 200
    # Week 42 (2026-10-12 to 10-16) and week 51 (2026-12-14 to 12-18) each contribute five titled rows.
    assert response.text.count("No teaching week") == 10


def test_wall_planner_hides_lesson_squares_on_a_no_teach_week(client, db, services):
    semester = services.semesters.create_semester(2026, "fall")
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    realization = services.realizations.add_realization(course.id, semester.id, "TTV24SP")
    # Inserted straight through the repository: @LessonService.add_lesson rejects a date inside a NoTeachWeek,
    # but rows already holding a stale Lesson must still render blocked.
    SqliteLessonRepository(db).add(realization.id, date(2026, 10, 13), time(8, 0), time(10, 0), "Inside", "")

    response = client.get(f"/?semester_id={semester.id}")

    assert "Inside" not in response.text
    assert "No teaching week" in response.text


def test_realizations_view_shows_a_no_teach_week_as_a_single_line(client, services):
    semester = services.semesters.create_semester(2026, "fall")
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    realization = services.realizations.add_realization(course.id, semester.id, "TTV24SP")
    services.lessons.add_lesson(
        realization.id, date(2026, 9, 16), time(8, 0), time(10, 0), "Before the week", ""
    )

    response = client.get(f"/realizations?realization_id={realization.id}")

    assert response.status_code == 200
    assert "No teaching week" in response.text
    assert "No teaching week \u2013" not in response.text
    assert "Before the week" in response.text


def test_realizations_view_appends_a_custom_no_teach_week_title(client, services):
    semester = services.semesters.create_semester(2026, "fall")
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    realization = services.realizations.add_realization(course.id, semester.id, "TTV24SP")
    week = next(w for w in services.no_teach_weeks.list_no_teach_weeks(semester.id) if w.week_number == 42)
    services.no_teach_weeks.update_no_teach_week(week.id, week.week_number, "Staff training")

    response = client.get(f"/realizations?realization_id={realization.id}")

    assert "No teaching week \u2013 Staff training" in response.text


# Current day and current week highlighting


def test_wall_planner_renders_a_green_bar_on_today(client, services, monkeypatch):
    semester = services.semesters.create_semester(2026, "fall")
    monkeypatch.setattr(dates, "today", lambda: FIXED_TODAY)

    response = client.get(f"/?semester_id={semester.id}")

    assert response.status_code == 200
    assert response.text.count("border-l-green-500") == 1


def test_wall_planner_renders_no_green_bar_when_today_is_outside_the_semester(client, services, monkeypatch):
    semester = services.semesters.create_semester(2027, "spring")
    monkeypatch.setattr(dates, "today", lambda: FIXED_TODAY)

    response = client.get(f"/?semester_id={semester.id}")

    assert response.status_code == 200
    assert "border-l-green-500" not in response.text


def test_realizations_view_renders_a_green_bar_on_the_current_week(client, services, monkeypatch):
    semester = services.semesters.create_semester(2026, "fall")
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    realization = services.realizations.add_realization(course.id, semester.id, "TTV24SP")
    monkeypatch.setattr(dates, "today", lambda: FIXED_TODAY)

    response = client.get(f"/realizations?realization_id={realization.id}")

    assert response.status_code == 200
    assert response.text.count("border-l-green-500") == 1


def test_realizations_view_renders_week_date_ranges_in_the_european_form(client, services):
    semester = services.semesters.create_semester(2026, "fall")
    course = services.courses.add_course("Machine Learning", "An introduction.", 5)
    realization = services.realizations.add_realization(course.id, semester.id, "TTV24SP")

    response = client.get(f"/realizations?realization_id={realization.id}")

    assert response.status_code == 200
    # Fall 2026 starts Saturday 2026-08-01, so its first table week runs Monday 2026-07-27 to Sunday 2026-08-02.
    assert "27.7.2026 \u2013 2.8.2026" in response.text
