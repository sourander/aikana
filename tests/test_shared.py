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


def test_pages_link_the_compiled_stylesheet_and_never_the_play_cdn(client):
    for path in ("/", "/courses", "/realizations"):
        response = client.get(path)
        assert 'href="/static/app.css"' in response.text
        assert "cdn.tailwindcss.com" not in response.text
        assert "htmx" in response.text
