from starlette.testclient import TestClient


def test_index_serves_empty_state_page(tmp_path, monkeypatch):
    # FastHTML writes a session key file into the working directory on import.
    monkeypatch.chdir(tmp_path)
    from aikana.shared import db

    monkeypatch.setattr(db, "DB_PATH", tmp_path / "app.db")
    from aikana.main import app

    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert "Aikana" in response.text
    assert "Create Semester" in response.text

