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
    code = chr(96)*3 + "python\\nimport os\\n" + chr(96)*3
    r=ext_client.post("/api/extensions/skills",json={"name":"Unsafe","content":code})
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


def test_oauth_secret_requires_master_key(ext_client):
    payload = {
        "name": "Provider",
        "authorization_url": "https://auth.example.com/authorize",
        "token_url": "https://auth.example.com/token",
        "client_id": "client-id",
        "client_secret": "never-store-plaintext",
        "redirect_uri": "https://app.example.com/api/extensions/oauth/callback",
        "scopes": ["profile"],
    }
    response = ext_client.post("/api/extensions/oauth/providers", json=payload)
    assert response.status_code == 503
    assert ext_client.get("/api/extensions/oauth/providers").json() == []


def test_oauth_provider_rejects_insecure_urls(ext_client):
    payload = {
        "name": "Insecure",
        "authorization_url": "http://auth.example.com/authorize",
        "token_url": "https://auth.example.com/token",
        "client_id": "client-id",
        "redirect_uri": "https://app.example.com/callback",
    }
    assert ext_client.post("/api/extensions/oauth/providers", json=payload).status_code == 400


def test_finance_proposal_requires_provider_and_never_executes(ext_client):
    provider = ext_client.post("/api/extensions/oauth/providers", json={
        "name": "Broker",
        "authorization_url": "https://broker.example.com/authorize",
        "token_url": "https://broker.example.com/token",
        "client_id": "client-id",
        "redirect_uri": "https://app.example.com/api/extensions/oauth/callback",
    })
    assert provider.status_code == 200
    proposal = ext_client.post("/api/extensions/finance/order-proposals", json={
        "provider_id": provider.json()["id"],
        "asset": "IVVB11",
        "side": "buy",
        "quantity": 1,
        "order_type": "market",
    })
    assert proposal.status_code == 200
    proposal_id = proposal.json()["id"]
    assert ext_client.post(f"/api/extensions/finance/order-proposals/{proposal_id}/approve").json()["status"] == "approved_not_executed"
    assert ext_client.post(f"/api/extensions/finance/order-proposals/{proposal_id}/execute").status_code == 501


def test_intel_only_accepts_https_evidence(ext_client):
    case = ext_client.post("/api/extensions/intel/cases", json={
        "query": "Example research",
        "purpose": "Validate publicly available information.",
    })
    assert case.status_code == 200
    cid = case.json()["id"]
    bad = ext_client.post(f"/api/extensions/intel/cases/{cid}/evidence", json={
        "url": "http://example.com/source",
        "title": "Insecure source",
    })
    assert bad.status_code == 400
    good = ext_client.post(f"/api/extensions/intel/cases/{cid}/evidence", json={
        "url": "https://example.com/source",
        "title": "Public source",
        "snippet": "A short excerpt.",
        "source_type": "public_web",
    })
    assert good.status_code == 200


def test_mcp_can_be_disabled_without_launching_process(ext_client):
    created = ext_client.post("/api/extensions/mcp", json={
        "name": "Stored only",
        "transport": "stdio",
        "command": "not-launched",
        "args": [],
    })
    sid = created.json()["id"]
    disabled = ext_client.post(f"/api/extensions/mcp/{sid}/disable")
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"


def test_mcp_tool_requires_individual_grant_and_explicit_approval(ext_client, monkeypatch):
    sid = "server-test"
    with extensions.db() as db:
        db.execute("INSERT INTO mcp_servers VALUES(?,?,?,?,?,?,?,?)", (sid,"Test MCP","streamable-http","https://mcp.example.com/mcp",None,"[]","registered_unverified",1.0))
        db.execute("INSERT INTO mcp_tools VALUES(?,?,?,?,?)", (sid,"lookup","Read-only lookup",'{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}',1.0))
    denied = ext_client.post(f"/api/extensions/mcp/{sid}/tools/lookup/proposals", json={"arguments":{"query":"test"}})
    assert denied.status_code == 403
    assert ext_client.post(f"/api/extensions/mcp/{sid}/tools/lookup/grant").json()["enabled"] is True
    bad_args = ext_client.post(f"/api/extensions/mcp/{sid}/tools/lookup/proposals", json={"arguments":{}})
    assert bad_args.status_code == 400
    proposal = ext_client.post(f"/api/extensions/mcp/{sid}/tools/lookup/proposals", json={"arguments":{"query":"test"}})
    assert proposal.status_code == 200
    assert proposal.json()["status"] == "pending_review"
    assert ext_client.get("/api/extensions/mcp/proposals").json()[0]["status"] == "pending_review"


def test_approved_skills_are_available_to_coworker_prompt(ext_client):
    created = ext_client.post("/api/extensions/skills", json={"name":"Cite sources","content":"Always cite URLs and dates."})
    sid = created.json()["id"]
    assert ext_client.post(f"/api/extensions/skills/{sid}/approve").status_code == 200
    assert "Always cite URLs and dates." in extensions.active_skill_instructions()
