import ast
import importlib
import json
import sys
from pathlib import Path

# Ensure the repository root is importable when pytest imports this file.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("KAMY_TESTING", "1")
    monkeypatch.setenv("KAMY_BROWSER_ENABLED", "0")
    import app as kamy
    monkeypatch.setattr(kamy, "DB", tmp_path / "kamy.sqlite3")
    monkeypatch.setattr(kamy, "DATA", tmp_path)
    monkeypatch.setattr(kamy, "WORK", tmp_path / "workspaces")
    kamy.WORK.mkdir(parents=True, exist_ok=True)
    kamy.init()
    with TestClient(kamy.app, client=("127.0.0.1", 50000)) as test_client:
        yield test_client, kamy


def test_python_syntax():
    from pathlib import Path
    ast.parse(Path("app.py").read_text(encoding="utf-8"))


def test_health_and_default_agents(client):
    http, _ = client
    assert http.get("/api/health").status_code == 200
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
    repeated = http.post(f"/api/actions/{pending['id']}/decision", json={"decision": "approve"})
    assert repeated.status_code == 409


def test_browser_is_explicitly_disabled_in_native_mode(client):
    http, _ = client
    response = http.get("/api/browser/nova/screenshot")
    assert response.status_code == 503


def test_workspace_path_traversal_is_rejected(client):
    _, kamy = client
    with pytest.raises(Exception):
        kamy.safe_path("nova", "../outside.txt")


def test_provider_api_keys_are_encrypted_at_rest(client, monkeypatch):
    http, kamy = client
    payload = {"name": "Secure", "role": "Analyst", "api_key": "secret-provider-key"}
    monkeypatch.setenv("KAMY_MASTER_KEY", "")
    assert http.post("/api/agents", json=payload).status_code == 503

    from cryptography.fernet import Fernet
    monkeypatch.setenv("KAMY_MASTER_KEY", Fernet.generate_key().decode())
    created = http.post("/api/agents", json=payload)
    assert created.status_code == 200
    with kamy.conn() as db:
        stored = db.execute("SELECT api_key FROM agents WHERE id=?", (created.json()["id"],)).fetchone()["api_key"]
    assert stored.startswith("fernet:")
    assert "secret-provider-key" not in stored


def test_remote_clients_are_rejected_by_default(client):
    _, kamy = client
    import os
    os.environ.pop("KAMY_TESTING", None)
    with TestClient(kamy.app, client=("192.0.2.10", 12345)) as remote:
        assert remote.get("/api/agents").status_code == 403

def test_docker_bridge_is_allowed_only_in_local_compose_mode(client, monkeypatch):
    _, kamy = client
    monkeypatch.setenv("KAMY_DOCKER_LOCAL", "1")
    with TestClient(kamy.app, client=("172.18.0.1", 12345)) as docker_bridge:
        assert docker_bridge.get("/api/health").status_code == 200
