import ast
import importlib
import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("KAMY_BROWSER_ENABLED", "0")
    import app as kamy
    monkeypatch.setattr(kamy, "DB", tmp_path / "kamy.sqlite3")
    monkeypatch.setattr(kamy, "DATA", tmp_path)
    monkeypatch.setattr(kamy, "WORK", tmp_path / "workspaces")
    kamy.WORK.mkdir(parents=True, exist_ok=True)
    kamy.init()
    with TestClient(kamy.app) as test_client:
        yield test_client, kamy


def test_python_syntax():
    from pathlib import Path
    ast.parse(Path("app.py").read_text(encoding="utf-8"))


def test_health_and_default_agents(client):
    http, _ = client
    assert http.get("/api/health").json()["ok"] is True
    agents = http.get("/api/agents").json()
    assert {agent["id"] for agent in agents} == {"nova", "pixel", "scout"}
    assert all("api_key" not in agent for agent in agents)


def test_create_agent_and_reject_unknown_tool(client):
    http, _ = client
    response = http.post("/api/agents", json={"name":"Orbit","role":"Analyst","tools":["shell.exec"]})
    assert response.status_code == 400
    response = http.post("/api/agents", json={"name":"Orbit","role":"Analyst"})
    assert response.status_code == 200
    assert response.json()["id"] == "orbit"


def test_policy_validation_and_audit(client):
    http, _ = client
    assert http.put("/api/agents/nova/policy", json={"domains":["example.com"],"tools":["shell.exec"]}).status_code == 400
    assert http.put("/api/agents/nova/policy", json={"domains":["https://example.com"],"tools":["browser.goto"]}).status_code == 400
    response = http.put("/api/agents/nova/policy", json={"domains":["example.com"],"tools":["browser.goto"]})
    assert response.status_code == 200
    actions = http.get("/api/actions").json()
    assert any(action["kind"] == "policy.update" for action in actions)


def test_demo_chat_and_reject_pending_action(client):
    http, _ = client
    response = http.post("/api/chat/nova", json={"message":"Abra https://example.com"})
    assert response.status_code == 200
    messages = http.get("/api/messages/nova").json()
    assert [message["role"] for message in messages] == ["user", "assistant"]
    actions = http.get("/api/actions").json()
    pending = next(action for action in actions if action["status"] == "pending")
    decision = http.post(f"/api/actions/{pending['id']}/decision", json={"decision":"reject"})
    assert decision.status_code == 200
    assert decision.json()["status"] == "rejected"


def test_workspace_path_traversal_is_rejected(client):
    _, kamy = client
    with pytest.raises(Exception):
        kamy.safe_path("nova", "../outside.txt")
