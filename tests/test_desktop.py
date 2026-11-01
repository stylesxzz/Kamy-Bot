import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_master_key_is_created_once_and_remains_stable(tmp_path, monkeypatch):
    import security

    monkeypatch.setenv("KAMY_TESTING", "1")
    monkeypatch.setenv("KAMY_MASTER_KEY", "")
    monkeypatch.setattr(security, "_read_key_from_env_file", lambda: None)

    first = security.ensure_local_master_key(tmp_path)
    key_file = tmp_path / ".master_key"

    assert key_file.exists()
    assert first == key_file.read_text(encoding="utf-8").strip()
    Fernet(first.encode("ascii"))

    # Simulate a fresh process where the environment variable is not present.
    monkeypatch.setenv("KAMY_MASTER_KEY", "")
    second = security.ensure_local_master_key(tmp_path)
    assert second == first

    if os.name != "nt":
        assert stat.S_IMODE(key_file.stat().st_mode) == 0o600


def test_settings_api_saves_key_when_environment_has_no_master_key(client, tmp_path, monkeypatch):
    http, kamy = client
    import security

    monkeypatch.setenv("KAMY_MASTER_KEY", "")
    monkeypatch.setattr(security, "_read_key_from_env_file", lambda: None)
    local_key = security.ensure_local_master_key(tmp_path)
    assert os.environ["KAMY_MASTER_KEY"] == local_key

    secret = "nvapi-persistent-local-test-key"
    response = http.put("/api/settings", json={
        "default_model": "meta/llama-3.3-70b-instruct",
        "default_api_key": secret,
    })

    assert response.status_code == 200, response.text
    assert response.json()["key_saved"] is True
    assert response.json()["default_api_key_configured"] is True

    with kamy.conn() as db:
        stored = db.execute(
            "SELECT value FROM app_settings WHERE key='default_api_key'"
        ).fetchone()["value"]

    assert stored.startswith("fernet:")
    assert secret not in stored
    assert kamy.reveal_secret(stored) == secret


def test_desktop_island_assets_and_voice_controls_exist():
    html = (PROJECT_ROOT / "static" / "index.html").read_text(encoding="utf-8")
    frontend = (PROJECT_ROOT / "static" / "app.js").read_text(encoding="utf-8")
    styles = (PROJECT_ROOT / "static" / "island.css").read_text(encoding="utf-8")
    desktop_main = (PROJECT_ROOT / "desktop" / "main.js").read_text(encoding="utf-8")
    preload = (PROJECT_ROOT / "desktop" / "preload.js").read_text(encoding="utf-8")

    assert 'id="desktopAgentSelect"' in html
    assert 'id="desktopExpand"' in html
    assert 'id="desktopCollapse"' in html
    assert 'id="voiceButton"' in html
    assert "SpeechRecognition" in frontend
    assert 'recognition.lang = "pt-BR"' in frontend
    assert "island-mode" in styles
    assert "expanded-mode" in styles
    assert "setAlwaysOnTop" in desktop_main
    assert "setFullScreen" in desktop_main
    assert "contextIsolation: true" in desktop_main
    assert "nodeIntegration: false" in desktop_main
    assert "contextBridge.exposeInMainWorld" in preload


def test_electron_is_an_optional_pinned_dependency():
    import json

    package = json.loads((PROJECT_ROOT / "package.json").read_text(encoding="utf-8"))
    assert package["version"] == "1.3.0"
    assert package["optionalDependencies"]["electron"] == "45.2.1"
    assert "desktop/" in package["files"]
