import pytest
from starlette.testclient import TestClient

from aikana.main import create_app
from aikana.shared.db import create_database

AIKANA_PASSWD = "test-password"


@pytest.fixture
def client(tmp_path, monkeypatch):
    # FastHTML writes a session key file into the working directory on app construction.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AIKANA_PASSWD", AIKANA_PASSWD)
    return TestClient(create_app(create_database(tmp_path / "app.db")))


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
