import pytest
from starlette.testclient import TestClient

AIKANA_PASSWD = "test-password"


@pytest.fixture
def client(tmp_path, monkeypatch):
    # FastHTML writes a session key file into the working directory on import.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AIKANA_PASSWD", AIKANA_PASSWD)
    from aikana.shared import db

    monkeypatch.setattr(db, "DB_PATH", tmp_path / "app.db")
    monkeypatch.setattr(db, "_db", None)
    from aikana.main import app

    return TestClient(app)


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
