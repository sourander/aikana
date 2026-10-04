"""Tests of the MCP server adapter: the write guard, the SDK-free service mapping and the mounted `/mcp`
endpoint's anonymous reads and token-gated writes, per ./tests.sdd.
"""

import pytest
from starlette.testclient import TestClient

from aikana.main import create_app
from aikana.mcp_server.services import McpError, McpService, McpWriteGuard

MCP_TOKEN = "test-mcp-token"

_INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 0,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-11-25",
        "capabilities": {},
        "clientInfo": {"name": "pytest", "version": "0"},
    },
}


@pytest.fixture
def mcp(services):
    """@McpService wrapping the shared `services` fixture."""
    return McpService(
        course_service=services.courses,
        semester_service=services.semesters,
        realization_service=services.realizations,
        lesson_service=services.lessons,
        holiday_service=services.holidays,
        no_teach_week_service=services.no_teach_weeks,
    )


def _post(client, payload, session_id=None, token=None):
    headers = {"Accept": "application/json, text/event-stream"}
    if session_id:
        headers["mcp-session-id"] = session_id
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return client.post("/mcp", json=payload, headers=headers)


def _call_tool(client, session_id, name, arguments=None, token=None, request_id=1):
    response = _post(
        client,
        {"jsonrpc": "2.0", "id": request_id, "method": "tools/call", "params": {"name": name, "arguments": arguments or {}}},
        session_id=session_id,
        token=token,
    )
    assert response.status_code == 200
    return response.json()["result"]


@pytest.fixture
def mcp_client(db, tmp_path, monkeypatch):
    """An in-process client with an initialized MCP session on a temporary database.

    The context manager runs the app's lifespan, which the SDK's session manager needs, per
    ../src/aikana/mcp_server/mcp_server.sdd.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AIKANA_PASSWD", "test-password")
    monkeypatch.setenv("AIKANA_MCP_TOKEN", MCP_TOKEN)
    with TestClient(create_app(db), base_url="https://testserver") as client:
        response = _post(client, _INITIALIZE)
        assert response.status_code == 200
        session_id = response.headers["mcp-session-id"]
        assert (
            _post(client, {"jsonrpc": "2.0", "method": "notifications/initialized"}, session_id).status_code == 202
        )
        yield client, session_id


# The write guard


def test_guard_allows_the_configured_token():
    assert McpWriteGuard(MCP_TOKEN).allows(MCP_TOKEN)


def test_guard_rejects_a_wrong_or_missing_token():
    guard = McpWriteGuard(MCP_TOKEN)
    assert not guard.allows("wrong-token")
    assert not guard.allows(None)


def test_guard_fails_closed_when_no_token_is_configured():
    assert not McpWriteGuard("").allows(MCP_TOKEN)


# The SDK-free service mapping


def test_semesters_are_serialized_with_iso_bounds(mcp):
    created = mcp.create_semester(2026, "fall")
    assert created == {"id": created["id"], "year": 2026, "term": "fall", "start": "2026-08-01", "end": "2026-12-31"}
    assert mcp.list_semesters() == [created]


def test_lesson_times_and_dates_are_serialized_as_iso_strings(mcp):
    course = mcp.create_course("Machine Learning", "An introduction.", 5)
    semester = mcp.create_semester(2026, "fall")
    realization = mcp.create_realization(course["id"], semester["id"], "TTV24SP")
    lesson = mcp.create_lesson(realization["id"], "2026-09-01", "08:00", "10:00", "Intro", "Room B")
    assert lesson["date"] == "2026-09-01"
    assert (lesson["start_time"], lesson["end_time"]) == ("08:00", "10:00")


def test_a_domain_error_becomes_an_mcp_error(mcp):
    mcp.create_course("Machine Learning", "An introduction.", 5)
    with pytest.raises(McpError, match="already exists"):
        mcp.create_course("machine learning", "Another one.", 5)


def test_an_unknown_read_becomes_an_mcp_error(mcp):
    with pytest.raises(McpError, match="No Course"):
        mcp.get_course(123)


def test_a_malformed_iso_date_becomes_an_mcp_error(mcp):
    with pytest.raises(McpError, match="yyyy-mm-dd"):
        mcp.create_holiday("6.12.2026", "Independence Day")


# The mounted `/mcp` endpoint


def test_tools_list_exposes_every_tool_anonymously(mcp_client):
    client, session_id = mcp_client
    response = _post(
        client, {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}, session_id=session_id
    )
    names = {tool["name"] for tool in response.json()["result"]["tools"]}
    assert names == {
        "list_semesters", "create_semester", "delete_semester",
        "list_courses", "get_course", "create_course", "update_course", "delete_course",
        "get_realization", "list_realizations", "create_realization", "update_realization", "delete_realization",
        "get_lesson", "list_lessons", "list_lessons_for_range", "create_lesson", "update_lesson", "delete_lesson",
        "list_holidays", "create_holiday", "update_holiday", "delete_holiday",
        "list_no_teach_weeks", "create_no_teach_week", "update_no_teach_week", "delete_no_teach_week",
    }


def test_read_tools_work_anonymously(mcp_client):
    client, session_id = mcp_client
    result = _call_tool(client, session_id, "list_semesters")
    assert result["isError"] is False
    # The SDK wraps a list return in an object with a `result` key for structured output.
    assert result["structuredContent"] == {"result": []}


def test_a_write_tool_is_rejected_without_a_token(mcp_client):
    client, session_id = mcp_client
    result = _call_tool(client, session_id, "create_course", {"name": "ML", "description": "Intro.", "ects_credits": 5})
    assert result["isError"] is True
    assert "AIKANA_MCP_TOKEN" in result["content"][0]["text"]


def test_a_write_tool_is_rejected_with_a_wrong_token(mcp_client):
    client, session_id = mcp_client
    result = _call_tool(
        client, session_id, "create_course", {"name": "ML", "description": "Intro.", "ects_credits": 5},
        token="wrong-token",
    )
    assert result["isError"] is True


def test_a_write_tool_works_with_the_token_and_the_read_tools_see_the_result(mcp_client):
    client, session_id = mcp_client
    created = _call_tool(
        client, session_id, "create_course", {"name": "ML", "description": "Intro.", "ects_credits": 5},
        token=MCP_TOKEN,
    )
    assert created["isError"] is False
    assert created["structuredContent"]["name"] == "ML"
    listed = _call_tool(client, session_id, "list_courses")
    assert [course["name"] for course in listed["structuredContent"]["result"]] == ["ML"]


def test_a_domain_error_over_the_wire_is_a_tool_error_not_a_protocol_error(mcp_client):
    client, session_id = mcp_client
    result = _call_tool(
        client, session_id, "create_semester", {"year": 2026, "term": "summer"}, token=MCP_TOKEN
    )
    assert result["isError"] is True
    assert "spring" in result["content"][0]["text"]


def test_writes_fail_closed_when_no_token_is_configured(db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AIKANA_PASSWD", "test-password")
    monkeypatch.delenv("AIKANA_MCP_TOKEN", raising=False)
    with TestClient(create_app(db), base_url="https://testserver") as client:
        session_id = _post(client, _INITIALIZE).headers["mcp-session-id"]
        _post(client, {"jsonrpc": "2.0", "method": "notifications/initialized"}, session_id)
        result = _call_tool(
            client, session_id, "create_course", {"name": "ML", "description": "Intro.", "ects_credits": 5},
            token=MCP_TOKEN,
        )
    assert result["isError"] is True


def test_the_html_routes_are_not_shadowed_by_the_mcp_mount(mcp_client):
    client, _ = mcp_client
    assert client.get("/courses").status_code == 200
