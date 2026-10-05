"""Tests of the shared kernel: the database factory and the page shell, per ./tests.sdd."""

from datetime import date

from aikana.shared import layout
from aikana.shared.db import create_database


def test_create_database_creates_a_missing_parent_directory(tmp_path):
    db = create_database(tmp_path / "missing" / "nested" / "app.db")

    # Opening the database would fail had the parent directory not been created.
    assert db.conn.execute("select 1").fetchone() == (1,)


def test_day_calendar_week_header_runs_from_monday_to_sunday():
    html = layout.day_calendar(date(2026, 10, 21)).__html__()

    # Every weekday label appears, in Monday-to-Sunday order, so the grid's week starts on Monday.
    positions = [html.index(f">{label}<") for label in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")]
    assert positions == sorted(positions)


def test_pages_link_the_stylesheet_and_it_is_served(client):
    for path in ("/", "/courses", "/realizations"):
        response = client.get(path)
        assert 'href="/static/app.css"' in response.text
        assert "htmx" in response.text

    # The stylesheet is hand-written source committed to the repository, so it is served without any build step.
    response = client.get("/static/app.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")


def test_pages_link_the_favicon_and_it_is_served(client):
    for path in ("/", "/courses", "/realizations"):
        assert 'href="/static/favicon.svg"' in client.get(path).text

    # The icon link would 404 without a static route for `.svg`, which the stylesheet's `.css` route does not serve.
    response = client.get("/static/favicon.svg")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
