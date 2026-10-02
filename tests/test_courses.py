"""In-process client tests of the courses page, its create form and its edit dialog, per ./tests.sdd."""

import pytest
from starlette.testclient import TestClient

from aikana.courses.repository_sqlite import SqliteCourseRepository
from aikana.courses.services import CourseService
from aikana.main import create_app
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
    return TestClient(create_app(db))


@pytest.fixture
def course_service(db):
    """Reads the same temporary database the app was built on, to look up Course ids."""
    return CourseService(SqliteCourseRepository(db))


@pytest.fixture
def admin_client(client):
    client.post("/login", data={"password": AIKANA_PASSWD}, follow_redirects=True)
    return client


def _create_course(client, name="Machine Learning", description="An introduction.", ects_credits=5):
    return client.post(
        "/courses",
        data={"name": name, "description": description, "ects_credits": str(ects_credits)},
        follow_redirects=True,
    )


def test_empty_courses_page_shows_the_create_form_to_the_admin(admin_client):
    response = admin_client.get("/courses")

    assert response.status_code == 200
    assert "Create a Course to get started." in response.text
    assert "Create Course" in response.text


def test_empty_courses_page_shows_a_notice_to_a_visitor(client):
    response = client.get("/courses")

    assert response.status_code == 200
    assert "No Course has been created yet." in response.text
    assert "Create Course" not in response.text


def test_admin_creates_a_course(admin_client):
    response = _create_course(admin_client)

    assert response.status_code == 200
    assert "Machine Learning" in response.text
    assert "An introduction." in response.text
    assert "5 ECTS" in response.text
    assert "+ New Course" in response.text


def test_create_course_rejects_an_empty_name(admin_client, course_service):
    response = _create_course(admin_client, name="   ")

    assert "A Course needs a non-empty name." in response.text
    assert course_service.list_courses() == []


def test_create_course_rejects_a_duplicate_name(admin_client, course_service):
    _create_course(admin_client)
    response = _create_course(admin_client, name="  machine learning ")

    assert "already exists" in response.text
    assert len(course_service.list_courses()) == 1


def test_courses_page_lists_courses_for_a_visitor_without_editing_affordances(admin_client):
    _create_course(admin_client)
    admin_client.post("/logout", follow_redirects=True)

    response = admin_client.get("/courses")

    assert "Machine Learning" in response.text
    assert "+ New Course" not in response.text
    assert "<dialog" not in response.text


def test_admin_courses_page_has_a_prefilled_edit_dialog(admin_client, course_service):
    _create_course(admin_client)
    course = course_service.list_courses()[0]

    response = admin_client.get("/courses")

    assert f'id="course-dialog-{course.id}"' in response.text
    assert f'action="/courses/{course.id}"' in response.text
    assert 'value="Machine Learning"' in response.text


def test_admin_updates_a_course(admin_client, course_service):
    _create_course(admin_client)
    course = course_service.list_courses()[0]

    response = admin_client.post(
        f"/courses/{course.id}",
        data={"name": "Deep Learning", "description": "Advanced.", "ects_credits": "8"},
        follow_redirects=True,
    )

    assert "Deep Learning" in response.text
    assert "Advanced." in response.text
    assert "8 ECTS" in response.text
    assert "Machine Learning" not in response.text


def test_update_course_rejects_a_duplicate_name(admin_client, course_service):
    _create_course(admin_client, name="Machine Learning")
    _create_course(admin_client, name="Databases")
    databases = next(course for course in course_service.list_courses() if course.name == "Databases")

    response = admin_client.post(
        f"/courses/{databases.id}",
        data={"name": "machine learning", "description": "", "ects_credits": "5"},
        follow_redirects=True,
    )

    assert "already exists" in response.text
    assert any(course.name == "Databases" for course in course_service.list_courses())


def test_update_an_unknown_course_is_rejected(admin_client):
    response = admin_client.post(
        "/courses/no-such-course",
        data={"name": "Machine Learning", "description": "", "ects_credits": "5"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "No Course with id" in response.text


def test_visitor_cannot_create_or_update_courses(client, course_service):
    response = client.post(
        "/courses",
        data={"name": "Machine Learning", "description": "", "ects_credits": "5"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login"

    response = client.post(
        "/courses/whatever",
        data={"name": "Machine Learning", "description": "", "ects_credits": "5"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert course_service.list_courses() == []


def test_courses_tab_sits_between_semester_and_realizations(client):
    response = client.get("/")

    semester = response.text.index(">Semester<")
    courses = response.text.index(">Courses<")
    realizations = response.text.index(">Realizations<")
    assert semester < courses < realizations
