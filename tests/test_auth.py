"""In-process client tests of the admin login and logout and the password's secrecy, per ./tests.sdd."""

from starlette.testclient import TestClient

from aikana.main import create_app
from conftest import AIKANA_PASSWD


def test_login_with_a_wrong_password_is_rejected(client):
    response = client.post("/login", data={"password": "not-the-password"}, follow_redirects=True)

    assert "Incorrect password." in response.text
    # The session stays a visitor's: writes are still rejected, per /src/aikana/auth/auth.sdd's guard.
    write = client.post(
        "/courses",
        data={"name": "Machine Learning", "description": "", "ects_credits": "5"},
        follow_redirects=False,
    )
    assert write.status_code == 303
    assert write.headers["location"] == "/login"


def test_login_is_impossible_without_a_configured_password(db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AIKANA_PASSWD", raising=False)
    client = TestClient(create_app(db))

    response = client.post("/login", data={"password": "anything"}, follow_redirects=True)

    assert "Incorrect password." in response.text
    assert 'action="/logout"' not in response.text


def test_login_is_impossible_with_an_empty_configured_password(db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AIKANA_PASSWD", "")
    client = TestClient(create_app(db))

    response = client.post("/login", data={"password": ""}, follow_redirects=True)

    assert "Incorrect password." in response.text
    assert 'action="/logout"' not in response.text


def test_logout_clears_the_admin_session(admin_client):
    admin_client.post("/logout", follow_redirects=True)

    response = admin_client.post(
        "/courses",
        data={"name": "Machine Learning", "description": "", "ects_credits": "5"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_the_shell_shows_a_login_link_to_a_visitor_and_a_logout_button_to_the_admin(client):
    visitor_page = client.get("/")
    assert 'href="/login"' in visitor_page.text
    assert "Log out" not in visitor_page.text

    client.post("/login", data={"password": AIKANA_PASSWD}, follow_redirects=True)
    admin_page = client.get("/")
    assert 'action="/logout"' in admin_page.text
    assert "Log out" in admin_page.text


def test_the_password_is_never_rendered(client):
    client.post("/login", data={"password": AIKANA_PASSWD}, follow_redirects=True)

    for path in ("/", "/login?error=1", "/courses", "/realizations"):
        assert AIKANA_PASSWD not in client.get(path).text
