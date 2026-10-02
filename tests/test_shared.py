"""Tests of the shared kernel: the database factory and the page shell, per ./tests.sdd."""

from aikana.shared.db import create_database


def test_create_database_creates_a_missing_parent_directory(tmp_path):
    db = create_database(tmp_path / "missing" / "nested" / "app.db")

    # Opening the database would fail had the parent directory not been created.
    assert db.conn.execute("select 1").fetchone() == (1,)


def test_pages_link_the_compiled_stylesheet_and_never_the_play_cdn(client):
    for path in ("/", "/courses", "/realizations"):
        response = client.get(path)
        assert 'href="/static/app.css"' in response.text
        assert "cdn.tailwindcss.com" not in response.text
        assert "htmx" in response.text
