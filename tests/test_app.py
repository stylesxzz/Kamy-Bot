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


def test_local_settings_are_persisted_and_provider_key_is_encrypted(client, monkeypatch):
    http, kamy = client
    from cryptography.fernet import Fernet

    monkeypatch.setenv("KAMY_MASTER_KEY", Fernet.generate_key().decode())
    secret = "nvapi-private-global-key"
    response = http.put("/api/settings", json={
        "default_model": "nvidia/meta/llama-3.3-70b-instruct",
        "default_api_key": secret,
        "apply_default_model": True,
    })
    assert response.status_code == 200
    assert response.json()["default_api_key_configured"] is True
    saved = http.get("/api/settings").json()
    assert saved["default_model"] == "nvidia/meta/llama-3.3-70b-instruct"
    assert saved["default_api_key_configured"] is True
    assert secret not in response.text
    with kamy.conn() as db:
        encrypted = db.execute("SELECT value FROM app_settings WHERE key='default_api_key'").fetchone()["value"]
        models = {row["model"] for row in db.execute("SELECT model FROM agents")}
    assert encrypted.startswith("fernet:")
    assert secret not in encrypted
    assert models == {"nvidia/meta/llama-3.3-70b-instruct"}
    agents = http.get("/api/agents").json()
    assert all(agent["configured"] and agent["uses_default_provider"] for agent in agents)


def test_individual_coworker_provider_can_be_updated_and_cleared(client, monkeypatch):
    http, kamy = client
    from cryptography.fernet import Fernet

    monkeypatch.setenv("KAMY_MASTER_KEY", Fernet.generate_key().decode())
    secret = "nvapi-private-agent-key"
    response = http.put("/api/agents/nova/provider", json={
        "model": "nvidia/llama-3.1-nemotron-ultra-253b-v1",
        "api_key": secret,
    })
    assert response.status_code == 200
    assert response.json()["configured"] is True
    with kamy.conn() as db:
        row = db.execute("SELECT model,api_key FROM agents WHERE id='nova'").fetchone()
    assert row["model"] == "nvidia/llama-3.1-nemotron-ultra-253b-v1"
    assert row["api_key"].startswith("fernet:")
    assert secret not in row["api_key"]

    cleared = http.put("/api/agents/nova/provider", json={
        "model": "nvidia/llama-3.1-nemotron-ultra-253b-v1",
        "clear_api_key": True,
    })
    assert cleared.status_code == 200
    with kamy.conn() as db:
        assert db.execute("SELECT api_key FROM agents WHERE id='nova'").fetchone()["api_key"] is None


def test_npm_launcher_metadata_and_help():
    import json
    import shutil
    import subprocess

    package = json.loads(Path("package.json").read_text(encoding="utf-8"))
    assert package["name"] == "kamy-bot"
    assert package["bin"]["kamy-bot"] == "bin/kamy-bot.js"
    if shutil.which("node"):
        result = subprocess.run(["node", "bin/kamy-bot.js", "--help"], check=True, capture_output=True, text=True)
        assert "npm exec --yes --package=./Kamy-Bot -- kamy-bot" in result.stdout



def test_settings_view_is_a_sibling_of_extensions_view():
    html = Path("static/index.html").read_text(encoding="utf-8")
    extensions_start = html.index('<section id="extensions"')
    settings_start = html.index('<section id="settings"')
    main_end = html.index("</main>", settings_start)

    # Each navigation view must be a sibling under <main>, not nested in another
    # .view section (a hidden parent would make the child view impossible to show).
    assert html[extensions_start:settings_start].rstrip().endswith("</section>")
    assert html[settings_start:main_end].count("<section") == html[settings_start:main_end].count("</section>")



def test_python_314_uses_pydantic_with_binary_core_wheel():
    requirements = Path("requirements.txt").read_text(encoding="utf-8")
    launcher = Path("bin/kamy-bot.js").read_text(encoding="utf-8")
    assert "pydantic==2.13.5" in requirements
    assert "--only-binary=pydantic-core" in launcher



def test_launcher_validates_and_uses_venv_before_starting():
    launcher = Path("bin/kamy-bot.js").read_text(encoding="utf-8")
    assert "sys.prefix != sys.base_prefix" in launcher
    assert "Installing requirements.txt" not in launcher
    assert "Instalando requirements.txt usando o Python do .venv" in launcher
    assert "VIRTUAL_ENV" in launcher
    assert "--setup-only" in launcher
    assert "import fastapi,uvicorn,httpx,pydantic,cryptography,jsonschema,mcp" in launcher
