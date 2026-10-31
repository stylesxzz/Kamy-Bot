import pytest
from fastapi.testclient import TestClient
import app
import extensions

@pytest.fixture()
def ext_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KAMY_BROWSER_ENABLED","0")
    monkeypatch.setenv("KAMY_MASTER_KEY","")
    monkeypatch.setattr(extensions,"DB",tmp_path/"extensions.sqlite3")
    extensions.init_db()
    with TestClient(app.app) as client:
        yield client

def test_skill_requires_review(ext_client):
    r=ext_client.post("/api/extensions/skills",json={"name":"Research","description":"Public research","content":"Cite sources and dates."})
    assert r.status_code==200
    sid=r.json()["id"]
    assert r.json()["status"]=="pending_review"
    assert ext_client.get("/api/extensions/skills").json()[0]["status"]=="pending_review"
    assert ext_client.post(f"/api/extensions/skills/{sid}/approve").json()["status"]=="enabled"

def test_skill_rejects_executable_payload(ext_client):
    r=ext_client.post("/api/extensions/skills",json={"name":"Unsafe","content":"import os; os.system('whoami')"})
    assert r.status_code==400

def test_mcp_registry_does_not_execute_stdio(ext_client):
    r=ext_client.post("/api/extensions/mcp",json={"name":"Local MCP","transport":"stdio","command":"python","args":["server.py"]})
    assert r.status_code==200
    assert r.json()["status"]=="registered_unverified"
    assert ext_client.get("/api/extensions/mcp").json()[0]["command"]=="python"

def test_remote_mcp_requires_https(ext_client):
    r=ext_client.post("/api/extensions/mcp",json={"name":"Remote","transport":"streamable-http","url":"http://example.com/mcp"})
    assert r.status_code==400

def test_financial_execution_is_disabled(ext_client):
    r=ext_client.post("/api/extensions/finance/order-proposals/not-a-real-id/execute")
    assert r.status_code==501
