<div align="center">
  <img src="assets/kamy-mark.svg" width="112" alt="Kamy Bot mark" />
  <h1>KAMY BOT</h1>
  <p><strong>Local AI Coworkers · NVIDIA NIM · Human-approved automation</strong></p>
  <p>Independent AI coworkers with private browser contexts, per-agent workspaces, approval gates and a persistent audit trail.</p>
  <img src="assets/brand-palette.svg" width="100%" alt="Kamy Bot visual identity and color palette" />
  <p><a href="https://github.com/stylesxzz/Kamy-Bot">Repository</a> · <a href="https://build.nvidia.com/">NVIDIA API Catalog</a> · <a href="https://docs.api.nvidia.com/nim/reference/llm-apis">NVIDIA NIM API docs</a></p>
</div>

## 1. About

Kamy Bot is a self-hosted AI coworker workspace. It starts with NOVA, PIXEL and SCOUT, each with a separate channel, configuration, browser context and file workspace. The user can create more coworkers, configure NVIDIA NIM, manage approved tools/domains and review actions before execution.

**Supported deployment modes**

| Platform | Recommended method | Browser automation |
|---|---|---|
| Windows 10/11 | Docker Desktop + Compose | Yes |
| macOS | Docker Desktop + Compose | Yes |
| Linux desktop/server | Docker Engine + Compose | Yes |
| Android / Termux | Debian via proot-distro + Python venv | Disabled in native mode |
| Other Linux ARM64 | Docker Engine if supported, otherwise Python venv | Depends on Playwright/Chromium support |

> Termux does not provide a normal Docker Engine service. The Android instructions use a Debian userspace under proot and run the API natively. Chat and NVIDIA connectivity work in this mode; Playwright browser tools are disabled. For the complete browser experience, run Kamy Bot on a computer/server and open it from the phone over your private network.

## 2. Features

- **Coworker channels:** independent conversations and configurations.
- **NVIDIA NIM:** OpenAI-compatible Chat Completions endpoint.
- **Private browser contexts:** separate Playwright contexts per coworker when browser mode is enabled.
- **Per-agent workspaces:** files scoped to `KAMY_DATA_DIR/workspaces/<agent-id>`.
- **Approval gate:** proposed browser/file actions are queued until explicitly approved or rejected.
- **Policy enforcement:** tool allowlists, exact approved-domain checks, URL scheme validation and workspace path checks are checked at execution time.
- **Audit trail:** proposals, decisions and outcomes persist in SQLite.
- **Bring your own coworker:** create agents and configure model, API key, tools and domains.
- **Responsive interface:** desktop, tablet and mobile layouts.

## 3. Visual identity

The UI uses a dark plum canvas, translucent glass surfaces, blurred color fields and this four-color accent system:

| Token | Hex | Role |
|---|---|---|
| Solar | `#F2CB30` | Primary highlight |
| Fuchsia | `#DA0090` | Active states |
| Violet | `#2C0E63` | Secondary depth |
| Midnight | `#12002E` | Core background |

## 4. NVIDIA NIM setup

Kamy Bot uses the NVIDIA OpenAI-compatible Chat Completions endpoint:

- API URL: `https://integrate.api.nvidia.com/v1/chat/completions`
- Authentication: `Authorization: Bearer NVIDIA_API_KEY`
- Default model: `meta/llama-3.3-70b-instruct`

1. Create an API key in [NVIDIA API Catalog settings](https://build.nvidia.com/settings).
2. Start Kamy Bot.
3. Select **Add a coworker** or configure an existing coworker through the UI.
4. Enter the NVIDIA API key and model identifier.
5. Save the coworker.

The key is stored server-side in the local SQLite database and is not returned by the agents API. Do not commit keys to Git or share the SQLite data volume.

Official references: [NVIDIA NIM LLM APIs](https://docs.api.nvidia.com/nim/reference/llm-apis) · [NVIDIA API Catalog](https://build.nvidia.com/).

## 5. Installation — Windows 10/11

### 5.1 Install prerequisites

1. Install **Docker Desktop for Windows**: https://docs.docker.com/desktop/setup/install/windows-install/
2. During setup, use the WSL 2 backend when offered.
3. Restart Windows if the installer requests it.
4. Open Docker Desktop and wait until the engine reports that it is running.
5. Open PowerShell and verify:

```powershell
docker --version
docker compose version
```

### 5.2 Download and start Kamy Bot

```powershell
git --version
```

If Git is missing, install it from https://git-scm.com/download/win, then reopen PowerShell.

```powershell
cd $HOME
git clone https://github.com/stylesxzz/Kamy-Bot.git
cd Kamy-Bot
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
```

Open http://localhost:8000.

### 5.3 View logs and stop

```powershell
docker compose logs -f kamy-bot
docker compose down
```

To start again:

```powershell
docker compose up -d
```

### 5.4 Optional: run without Docker (no browser)

Install Python 3.11 or 3.12 from https://www.python.org/downloads/ and enable **Add Python to PATH**.

```powershell
cd $HOME
git clone https://github.com/stylesxzz/Kamy-Bot.git
cd Kamy-Bot
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
$env:KAMY_BROWSER_ENABLED="0"
$env:KAMY_DATA_DIR="$HOME\.kamy-bot"
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Browser actions are unavailable in this mode.

## 6. Installation — macOS

### 6.1 Install prerequisites

1. Install Docker Desktop for Mac: https://docs.docker.com/desktop/setup/install/mac-install/
2. Open Docker Desktop and wait for it to finish starting.
3. Open Terminal and verify:

```bash
docker --version
docker compose version
git --version
```

If Git is missing, install Apple's Command Line Tools:

```bash
xcode-select --install
```

### 6.2 Clone and run

```bash
cd "$HOME"
git clone https://github.com/stylesxzz/Kamy-Bot.git
cd Kamy-Bot
cp .env.example .env
docker compose up --build -d
docker compose ps
```

Open http://localhost:8000.

### 6.3 Logs, stop and restart

```bash
docker compose logs -f kamy-bot
docker compose down
docker compose up -d
```

### 6.4 Optional: native Python mode (no browser)

Install Python 3.11 or 3.12 (for example from https://www.python.org/downloads/macos/), then:

```bash
cd "$HOME"
git clone https://github.com/stylesxzz/Kamy-Bot.git
cd Kamy-Bot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
export KAMY_BROWSER_ENABLED=0
export KAMY_DATA_DIR="$HOME/.kamy-bot"
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000.

## 7. Installation — Linux (Docker Engine)

These commands cover Debian/Ubuntu. Other distributions should use the official Docker installation guide for their package manager: https://docs.docker.com/engine/install/.

### 7.1 Debian / Ubuntu prerequisites

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
```

For **Ubuntu**:

```bash
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

For **Debian** (including Debian-based distributions; Kali users may need to use the matching Debian codename):

```bash
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

Install Docker Engine, Buildx and the Compose plugin:

```bash
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker run hello-world
docker compose version
```

If your Linux distribution uses a different package manager (Fedora, Arch, openSUSE, etc.), follow https://docs.docker.com/engine/install/ and install the Docker Compose plugin as documented at https://docs.docker.com/compose/install/linux/.

> If Docker commands require root, prefix them with `sudo`. Adding your account to the `docker` group grants effectively root-level privileges; understand that security implication before doing so.

### 7.2 Clone and start the project

```bash
cd "$HOME"
git clone https://github.com/stylesxzz/Kamy-Bot.git
cd Kamy-Bot
cp .env.example .env
chmod +x start.sh
./start.sh
```

Open http://localhost:8000.

### 7.3 Operations

```bash
docker compose ps
docker compose logs -f kamy-bot
docker compose restart kamy-bot
docker compose down
docker compose up -d
```

## 8. Installation — Android / Termux

> **Important:** Docker Engine is not supported as a normal service inside Termux/proot. This guide runs the API directly in a Debian userspace. Browser automation is disabled; use a computer/server for full Playwright browser functionality.

### 8.1 Install Termux

Install Termux from a trusted source such as [F-Droid](https://f-droid.org/packages/com.termux/) or the official [Termux GitHub](https://github.com/termux/termux-app). Avoid mixing Termux APKs from different sources.

Open Termux and run:

```bash
pkg update -y && pkg upgrade -y
pkg install -y git proot-distro
```

### 8.2 Install Debian inside Termux

```bash
proot-distro install debian
proot-distro login debian
```

The following commands run **inside the Debian shell**:

```bash
apt update
apt upgrade -y
apt install -y git python3 python3-venv python3-pip build-essential
```

### 8.3 Clone and install Kamy Bot

```bash
cd "$HOME"
git clone https://github.com/stylesxzz/Kamy-Bot.git
cd Kamy-Bot
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 8.4 Start in Android mode

```bash
export KAMY_BROWSER_ENABLED=0
export KAMY_DATA_DIR="$HOME/.local/share/kamy-bot"
mkdir -p "$KAMY_DATA_DIR"
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Open the Android browser at http://127.0.0.1:8000. Keep the Termux session alive while using the app.

To stop the server, press **CTRL+C** in the terminal. To start it again, reopen Termux, enter Debian and run:

```bash
proot-distro login debian
cd "$HOME/Kamy-Bot"
. .venv/bin/activate
export KAMY_BROWSER_ENABLED=0
export KAMY_DATA_DIR="$HOME/.local/share/kamy-bot"
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

For access from another device on the same trusted Wi-Fi, change the host to `0.0.0.0` and open `http://ANDROID-LAN-IP:8000`. Do not expose this unauthenticated development server to the public internet.

## 9. Native Python installation — any supported OS

This method runs the API without Docker and without browser automation. It is useful on Linux, macOS, Windows and ARM64 systems where Docker is unavailable.

Requirements: Python 3.11 or 3.12 and Git.

1. Clone the repository:

```bash
git clone https://github.com/stylesxzz/Kamy-Bot.git
cd Kamy-Bot
```

2. Create and activate a virtual environment:

**Linux / macOS / Termux Debian**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows PowerShell**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies and start:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Linux / macOS**

```bash
export KAMY_BROWSER_ENABLED=0
export KAMY_DATA_DIR="$HOME/.kamy-bot"
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

**Windows PowerShell**

```powershell
$env:KAMY_BROWSER_ENABLED="0"
$env:KAMY_DATA_DIR="$HOME\.kamy-bot"
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Then open http://127.0.0.1:8000.

## 10. Configuration

The Compose deployment reads settings from `.env`:

```dotenv
KAMY_PORT=8000
KAMY_BROWSER_ENABLED=1
```

- `KAMY_PORT`: host port exposed by Docker Compose.
- `KAMY_BROWSER_ENABLED`: `1` enables Playwright (Docker deployment); `0` disables browser automation (native/Termux mode).
- `KAMY_DATA_DIR`: internal data directory. Docker sets it to `/data`; native installs can set it to a persistent directory in the user's home.

NVIDIA API keys are entered per coworker in the app. Do not put secrets in source files or commit `.env`.

## 11. Tests and validation

Install core dependencies and test tools:

```bash
python -m pip install -r requirements.txt pytest
python -m compileall -q app.py tests
pytest -q
node --check static/app.js
```

GitHub Actions runs the Python syntax checks, pytest suite and JavaScript syntax check on Python 3.11 and 3.12 for pushes and pull requests.

For a local Docker configuration check:

```bash
docker compose config -q
```

For a full container build and startup:

```bash
docker compose up --build -d
docker compose ps
curl http://localhost:8000/api/health
```

## 12. Data, logs and reset

Docker persists data in the named volume `kamy_data`. This includes agent configuration, NVIDIA keys, conversations, action history and agent workspaces.

```bash
docker compose logs -f kamy-bot
docker compose down
docker compose up -d
```

**Destructive reset:** this permanently removes the database, stored keys, conversations, audit records and workspaces:

```bash
docker compose down -v
```

Native mode stores data in the directory configured by `KAMY_DATA_DIR`. Back up that directory before upgrading or deleting the project.

## 13. Architecture

```text
Browser UI
   |
   v
FastAPI ---------------- NVIDIA NIM Chat Completions
   |
   +-- SQLite (agents, conversations, audit events)
   +-- Policy gate (tools, domains, workspace paths)
   +-- Playwright Chromium (optional, one BrowserContext per agent)
   +-- Per-agent workspace directories
```

## 14. Security model and known limitations

Kamy Bot is a local-first MVP, not a hardened multi-tenant execution sandbox.

- Browser contexts isolate cookies and storage but share a Chromium process; they are not OS-level isolation.
- The container does not mount the host filesystem or Docker socket.
- No general-purpose shell execution tool is exposed.
- Domain allowlists use exact hostname matching. This is not a complete DNS-rebinding or network-layer SSRF defense.
- API keys are stored in the local SQLite data volume. Protect the host and volume; encryption at rest is not implemented.
- The app currently has no built-in user authentication. Keep it bound to localhost or a trusted private network. Do not expose it directly to the public internet.
- Browser and file operations require approval, but approval does not replace network isolation, authentication or operating-system sandboxing.
- The coworker action proposal layer is currently a limited intent parser for supported URL/file requests, not a general autonomous function-calling runtime.

For an internet-facing deployment, add authentication, HTTPS, CSRF protection, rate limiting, secure secret storage, network egress filtering and stronger per-agent isolation first.

## 15. Project structure

```text
.
├── app.py
├── requirements.txt
├── requirements-browser.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── start.sh
├── start.bat
├── assets/
│   ├── kamy-mark.svg
│   └── brand-palette.svg
├── static/
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── empty.svg
├── tests/
│   └── test_app.py
└── .github/
    └── workflows/
        └── ci.yml
```

## 16. License

MIT. See [LICENSE](LICENSE).

## 17. Modular extensions — Finance, MCP, OAuth and Kamy Intel

The extension API is additive. The original NOVA / PIXEL / SCOUT coworker routes, NVIDIA NIM, browser approval, workspaces and audit workflow remain available.

### Master encryption key
OAuth client secrets and access/refresh tokens are encrypted at rest with Fernet. Generate a persistent key once:
~~~bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
~~~
Set it as KAMY_MASTER_KEY in the private deployment environment. Back it up securely: losing it makes previously encrypted tokens unrecoverable. Never commit it.

### Skills API
- GET /api/extensions/skills — list skills.
- POST /api/extensions/skills — submit declarative Markdown for review.
- POST /api/extensions/skills/{id}/approve — enable a reviewed skill.
- POST /api/extensions/skills/{id}/disable — disable it.

The initial installer accepts instruction-only Markdown. It does not execute downloaded Python, shell or JavaScript. Review external skill repositories before trusting their instructions.

### MCP registry
- GET /api/extensions/mcp — list configured servers.
- POST /api/extensions/mcp — register streamable-http, sse or stdio configuration.
- POST /api/extensions/mcp/{id}/disable — disable a registration.

Remote MCP endpoints must use HTTPS. HTTP is allowed only for loopback development endpoints. STDIO commands are stored as configuration and are not launched by this registry. This initial release provides registration metadata, not yet a general MCP client/tool execution runtime. Do not register untrusted servers.

### OAuth provider setup
Register a provider with its official authorization URL, token URL, client ID, exact HTTPS callback URI and minimum scopes. Then call POST /api/extensions/oauth/{provider_id}/start and open the returned authorization_url in the user's browser. The callback exchanges the code using PKCE S256 and stores tokens encrypted. Register the callback URI exactly in the provider console. The app does not collect passwords, bypass MFA, or automate credential entry. Provider-specific refresh, revocation and API adapters remain follow-up work.

### Finance workflow
- POST /api/extensions/finance/order-proposals — create a buy/sell proposal.
- GET /api/extensions/finance/order-proposals — list proposals.
- POST /api/extensions/finance/order-proposals/{id}/approve — approve for adapter integration.
- POST /api/extensions/finance/order-proposals/{id}/execute — deliberately returns HTTP 501 until a reviewed provider-specific trading adapter is implemented.

The current layer supports proposal and approval tracking only; it does not send orders or claim compatibility with every broker. Financial institutions have different APIs, eligibility, scopes and contractual restrictions. Use official APIs and user-authorized consent. Never provide brokerage passwords or private keys to the agent.

### Kamy Intel — evidence ledger
- POST /api/extensions/intel/cases — create a research case with a stated purpose.
- GET /api/extensions/intel/cases — list cases.
- POST /api/extensions/intel/cases/{id}/evidence — attach a public HTTPS source, excerpt and observation date.
- GET /api/extensions/intel/cases/{id}/evidence — retrieve evidence.

This is an evidence ledger, not an automatic social-network scraper. Platform searches must use public information or official APIs with user-authorized read-only scopes. Do not use it for private-account access, doxxing, stalking or bypassing platform controls. Distinguish verified facts from hypotheses and record source URLs and dates.

### Current implementation boundary
This release adds extension APIs and persistence. It does not yet include a visual extension marketplace, universal MCP execution engine, provider-specific brokerage adapters, automatic OAuth discovery for every provider, or automatic social-platform search connectors. Those require provider-specific implementation and tests.
