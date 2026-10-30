<div align="center">
  <img src="assets/kamy-mark.svg" width="112" alt="Kamy Bot mark" />
  <h1>KAMY BOT</h1>
  <p><strong>Local AI Coworkers · NVIDIA NIM · Human-approved automation</strong></p>
  <p>Independent AI coworkers with private browser contexts, isolated workspaces, explicit approval gates and a persistent audit trail.</p>
  <img src="assets/brand-palette.svg" width="100%" alt="Kamy Bot visual identity and color palette" />
  <p><a href="https://github.com/stylesxzz/Kamy-Bot">Repository</a> · <a href="https://build.nvidia.com/">NVIDIA API Catalog</a> · <a href="https://docs.api.nvidia.com/nim/reference/llm-apis">NVIDIA NIM API docs</a></p>
</div>

## Overview

Kamy Bot is a self-hosted AI coworker workspace. Start with example agents, chat in separate channels, inspect browser activity, manage per-agent boundaries and review every proposed action in an audit trail. It is designed for local experimentation and keeps provider credentials on the server side.

### Visual identity

The interface uses a dark plum canvas, translucent glass surfaces, soft blurred color fields and a four-color accent system based on the supplied reference:

| Token | Hex | Role |
|---|---|---|
| Solar | `#F2CB30` | Primary highlight |
| Fuchsia | `#DA0090` | Energy / active states |
| Violet | `#2C0E63` | Secondary depth |
| Midnight | `#12002E` | Core background |

## Core capabilities

- **Coworker channels:** NOVA (research), PIXEL (development) and SCOUT (browser operations).
- **Private browser contexts:** separate Playwright contexts per coworker, including independent cookies and storage.
- **Per-agent workspaces:** files are scoped to `/data/workspaces/<agent-id>` with path traversal protection.
- **Approval gate:** browser and file actions are queued; the user must approve or reject them before execution.
- **Policy enforcement:** tool allowlists, exact approved-domain checks, URL scheme validation and workspace boundaries are checked again at execution time.
- **Audit trail:** action proposals, decisions, outcomes, timestamps and errors are persisted in SQLite.
- **Bring your own coworker:** create additional agents and configure a model plus a NVIDIA API key.
- **Docker-first:** one start script, named persistent volume, health check and no host filesystem or Docker socket mount.

## NVIDIA NIM integration

Kamy Bot uses NVIDIA's OpenAI-compatible Chat Completions endpoint:

- Base URL: `https://integrate.api.nvidia.com/v1`
- Endpoint: `POST /chat/completions`
- Authentication: `Authorization: Bearer NVIDIA_API_KEY`
- Default model: `meta/llama-3.3-70b-instruct`

Create an API key at [build.nvidia.com/settings](https://build.nvidia.com/settings). Add the key to an agent in the app. Keys are stored server-side in the local SQLite database and are never returned by the agents API. Never commit API keys to Git.

NVIDIA documents the hosted NIM endpoint as OpenAI Chat Completions compatible. See [NVIDIA NIM LLM APIs](https://docs.api.nvidia.com/nim/reference/llm-apis) and [NVIDIA API Catalog](https://build.nvidia.com/).

## Quick start

### Requirements

- Docker Engine + Docker Compose plugin, or Docker Desktop
- 2 GB RAM available to Docker (more recommended for Chromium)
- NVIDIA API key (optional for demo mode; required for model responses)

### Linux / macOS

```bash
chmod +x start.sh
./start.sh
```

### Windows

Double-click `start.bat`, or run it from Command Prompt.

Open **http://localhost:8000**. The first startup builds the container and downloads the Playwright browser image.

### Stop and restart

```bash
docker compose down
docker compose up -d
```

Persistent data is stored in the Docker volume `kamy_data`. To permanently erase agent data, messages, credentials and audit records:

```bash
docker compose down -v
```

## Demo workflow

1. Open NOVA, PIXEL or SCOUT.
2. Ask: `Abra https://example.com e salve notas/visita.txt`
3. Review the pending browser and file actions.
4. Approve or reject each action.
5. Inspect the browser screenshot and audit trail.

The default allowlist contains only `example.com`. Add other domains from the policy screen before requesting navigation to them.

## Architecture

```text
Browser UI
   │
   ▼
FastAPI ───── NVIDIA NIM Chat Completions
   │
   ├── SQLite (agents, conversations, audit events)
   ├── Policy gate (tools, domains, workspace boundaries)
   ├── Playwright Chromium (one BrowserContext per agent)
   └── /data/workspaces/<agent-id>/
```

## Security model and limitations

Kamy Bot is a local-first MVP, not a hardened multi-tenant execution sandbox.

- Browser contexts isolate cookies and storage, but share a Chromium process; they are **not** OS-level isolation.
- The container does not mount the host filesystem or Docker socket. Only its named data volume is mounted.
- No general shell tool is exposed.
- Domain allowlists are exact-match checks. The current implementation blocks common local hostnames but is not a complete DNS-rebinding or network-layer SSRF defense.
- For untrusted agents or hostile websites, deploy browser workers in separate containers with egress filtering, stronger IP-range validation, resource limits and hardened Chromium sandboxing.
- API keys are stored in the local SQLite volume. Protect the machine and volume; add encryption at rest and authentication before exposing the app beyond localhost.
- The approval UI is the human control point. Do not expose the service publicly without authentication, TLS, CSRF protection and rate limiting.

## Project structure

```text
.
├── app.py
├── assets/
│   ├── kamy-mark.svg
│   └── brand-palette.svg
├── static/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── start.sh
├── start.bat
└── LICENSE
```

## License

MIT. See [LICENSE](LICENSE).
