from starlette.testclient import TestClient


def test_index_serves_page(tmp_path, monkeypatch):
    # FastHTML writes a session key file into the working directory on import.
    monkeypatch.chdir(tmp_path)
    from aikana.main import app

    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert "Aikana" in response.text
