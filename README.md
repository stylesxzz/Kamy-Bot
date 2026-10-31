<div align="center">
  <img src="assets/kamy-mascot.svg" width="120" alt="Mascote oficial da Kamy Bot">
  <h1>KAMY BOT</h1>
  <p><strong>AI Coworker Studio · Self-hosted · Human-supervised automation</strong></p>
  <p>Um ambiente modular de trabalho com IA, coworkers independentes, ferramentas controladas, workspaces isolados por agente e trilha de auditoria.</p>
  <p>
    <a href="https://github.com/stylesxzz/Kamy-Bot">Repositório</a> ·
    <a href="https://docs.api.nvidia.com/nim/reference/llm-apis">NVIDIA NIM API</a> ·
    <a href="https://modelcontextprotocol.io/">Model Context Protocol</a>
  </p>
</div>

---

## Visão geral

**Kamy Bot** é uma aplicação self-hosted que transforma modelos de linguagem em coworkers de IA configuráveis. Em uma única interface, o usuário conversa com agentes separados, configura provedores de IA, define políticas de ferramentas e domínios, revisa ações pendentes e acompanha os registros de atividade.

O projeto preserva uma arquitetura simples e extensível baseada em **Python, FastAPI, SQLite, HTML/CSS/JavaScript e Docker**. O mascote enviado para o projeto foi incorporado à identidade visual em \`assets/kamy-mascot.svg\`.

### Principais recursos

- **Coworkers independentes:** NOVA, PIXEL, SCOUT e agentes adicionais criados pelo usuário.
- **Modelos de IA:** integração atual com NVIDIA NIM; modelo e chave configuráveis por coworker.
- **Browser workspace:** automação Playwright/Chromium opcional, com contexto separado por coworker.
- **Human approval gate:** ações suportadas aguardam aprovação explícita.
- **Permissions:** allowlist de ferramentas e domínios por coworker.
- **Workspaces:** arquivos organizados em diretórios separados por agente.
- **Audit trail:** histórico de ações, decisões e resultados.
- **Skills:** cadastro, revisão e injeção automática de Skills aprovadas no prompt dos coworkers (limite de 8 Skills / 6.000 caracteres).
- **MCP runtime:** descoberta de ferramentas via Streamable HTTP, allowlist de host, permissão individual por ferramenta, validação JSON Schema e execução somente após aprovação explícita.
- **Connect / OAuth:** fluxo Authorization Code + PKCE e armazenamento criptografado de tokens.
- **Finance:** registro e aprovação de propostas; envio de ordens reais permanece bloqueado.
- **Kamy Intel:** casos de pesquisa e evidências provenientes de fontes públicas ou APIs autorizadas.

> **Estado do produto:** Kamy Bot é um MVP funcional em evolução. Os coworkers, chat, políticas, aprovação, workspaces e auditoria fazem parte da aplicação atual. O Kamy é um aplicativo single-user executado localmente: não possui login administrativo, cadastro de usuários ou serviço multi-tenant. O runtime MCP suporta Streamable HTTP e STDIO local. O processo STDIO é iniciado somente para descoberta e execução de ferramentas aprovadas, sem shell e sem herdar as chaves de API do processo Kamy. Não confunda cadastro com conexão efetiva.

## Coworkers

| Agente | Papel de referência |
|---|---|
| **NOVA** | Pesquisa, síntese e organização de informações. |
| **PIXEL** | Desenvolvimento, arquivos e tarefas técnicas. |
| **SCOUT** | Navegação supervisionada e coleta de evidências. |

Os três são agentes configuráveis, não serviços externos separados. Cada coworker possui suas próprias configurações, histórico e workspace. O comportamento final depende das instruções, do modelo e das permissões que o operador configurar.

## Arquitetura

\`\`\`text
Browser / Mobile
       |
       v
Web UI (HTML · CSS · JavaScript)
       |
       v
FastAPI application
  |       |        |         |
  v       v        v         v
Agents  Policies  Approval  Extensions API
  |       |        |         |
  v       v        v         +-- Skills registry
NVIDIA   Domain    Audit     +-- MCP registry
NIM      allowlist SQLite    +-- OAuth / PKCE
  |                         +-- Finance proposals
  v                         +-- Kamy Intel evidence
Playwright / Chromium
       |
       v
Per-agent workspaces + SQLite data volume
\`\`\`

### Stack

- Python 3.11+
- FastAPI e Uvicorn
- SQLite
- HTTPX
- Pydantic
- Playwright e Chromium (modo Docker com navegador)
- Cryptography / Fernet (segredos e tokens OAuth)
- HTML, CSS e JavaScript sem framework obrigatório
- Docker e Docker Compose

## Requisitos

### Método recomendado — Docker

- Docker Engine com Docker Compose v2 no Linux; ou Docker Desktop no Windows/macOS.
- Git.
- Porta local 8000 disponível (ou outra definida em \`.env\`).

### Execução nativa

- Python 3.11 ou superior.
- Git.
- Pip e suporte a ambientes virtuais.
- Navegador automatizado desabilitado (\`KAMY_BROWSER_ENABLED=0\`). O modo nativo é adequado para Termux/Android, mas não instala nem inicia Chromium.

## Instalação rápida com Docker

### Linux

\`\`\`bash
sudo apt update
sudo apt install -y git
git clone https://github.com/stylesxzz/Kamy-Bot.git
cd Kamy-Bot
cp .env.example .env
\`\`\`

### macOS

\`\`\`bash
xcode-select --install
git clone https://github.com/stylesxzz/Kamy-Bot.git
cd Kamy-Bot
cp .env.example .env
\`\`\`

### Windows — PowerShell

Instale Git e Docker Desktop, abra o PowerShell e execute:

\`\`\`powershell
git clone https://github.com/stylesxzz/Kamy-Bot.git
Set-Location Kamy-Bot
Copy-Item .env.example .env
\`\`\`

### Inicie o serviço (Linux, macOS, Windows)

Antes de iniciar, edite o arquivo \`.env\` se desejar alterar a porta, desabilitar o navegador ou configurar OAuth.

\`\`\`bash
docker compose up --build -d
docker compose ps
\`\`\`

Abra **http://127.0.0.1:8000**. A porta é vinculada a \`127.0.0.1\` por padrão para não publicar a interface na rede local sem intenção.

Atalhos incluídos:
- Linux/macOS: \`./start.sh\`
- Windows: execute \`start.bat\` no Explorador ou no Prompt de Comando.

## Acesso remoto opcional

O Kamy é local-first e bloqueia conexões que não sejam loopback. Não publique a porta 8000 nem altere `KAMY_BIND` para `0.0.0.0`. Se precisar acessar de outro dispositivo, configure uma VPN privada ou túnel autenticado que encaminhe a conexão ao `127.0.0.1` da máquina; não exponha o servidor diretamente à Internet.

## Instalação nativa (sem Docker)

O Kamy é um aplicativo individual. Instale no seu computador e use as credenciais das suas próprias contas.

### Linux e macOS
```bash
git clone https://github.com/stylesxzz/Kamy-Bot.git
cd Kamy-Bot
bash scripts/install.sh
bash scripts/start.sh
``

### Windows (PowerShell)
```powershell
git clone https://github.com/stylesxzz/Kamy-Bot.git
cd Kamy-Bot
powershell -ExecutionPolicy Bypass -File scripts/install.ps1
.\scripts\start.ps1
``

### Android (Termux)
```bash
pkg install git
git clone https://github.com/stylesxzz/Kamy-Bot.git
cd Kamy-Bot
bash scripts/install-termux.sh
bash scripts/start.sh
``

Abra `http://127.0.0.1:8765`. A instalação cria uma chave Fernet local em `.env`; faça backup seguro do arquivo e do diretório `data/`. Nunca publique segredos no Git.

## Comandos de operação Docker

Executar / reconstruir:

\`\`\`bash
docker compose up --build -d
\`\`\`

Ver estado e healthcheck:

\`\`\`bash
docker compose ps
curl http://127.0.0.1:8000/api/health
\`\`\`

Acompanhar logs:

\`\`\`bash
docker compose logs -f kamy-bot
\`\`\`

Reiniciar:

\`\`\`bash
docker compose restart kamy-bot
\`\`\`

Parar sem apagar dados:

\`\`\`bash
docker compose down
\`\`\`

Atualizar o código local e reconstruir:

\`\`\`bash
git pull
docker compose up --build -d
\`\`\`

**Atenção:** \`docker compose down -v\` remove o volume persistente \`kamy_data\` e apaga os dados do Kamy Bot. Use apenas se realmente quiser eliminar o banco e os workspaces.

## Instalação nativa — Linux e macOS

### Ubuntu / Debian

\`\`\`bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip
git clone https://github.com/stylesxzz/Kamy-Bot.git
cd Kamy-Bot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
# Edite .env e configure KAMY_MASTER_KEY.
set -a; . ./.env; set +a
export KAMY_BROWSER_ENABLED=0
uvicorn app:app --host 127.0.0.1 --port 8000
\`\`\`

### macOS

Com Python 3.11+ e Git instalados:

\`\`\`bash
git clone https://github.com/stylesxzz/Kamy-Bot.git
cd Kamy-Bot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
# Edite .env e configure KAMY_MASTER_KEY.
# Configure KAMY_MASTER_KEY no .env para armazenar credenciais.
set -a; . ./.env; set +a
export KAMY_BROWSER_ENABLED=0
uvicorn app:app --host 127.0.0.1 --port 8000
\`\`\`

Abra http://127.0.0.1:8000. Para encerrar, pressione \`Ctrl+C\`.

## Instalação nativa — Windows PowerShell

Instale Python 3.11+ e Git. Em seguida:

\`\`\`powershell
git clone https://github.com/stylesxzz/Kamy-Bot.git
Set-Location Kamy-Bot
py -3.11 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
# Edite .env e configure KAMY_MASTER_KEY.
$env:KAMY_BROWSER_ENABLED = "0"
python -m uvicorn app:app --host 127.0.0.1 --port 8000
\`\`\`

Se o PowerShell bloquear a ativação do ambiente virtual, execute apenas para a sessão atual:

\`\`\`powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\\.venv\\Scripts\\Activate.ps1
\`\`\`

## Instalação nativa — Termux / Android

Este é o modo sem navegador automatizado. Use Termux atualizado:

\`\`\`bash
pkg update && pkg upgrade -y
pkg install -y git python clang rust openssl libffi
git clone https://github.com/stylesxzz/Kamy-Bot.git
cd Kamy-Bot
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
# Edite .env e configure KAMY_MASTER_KEY.
# O Kamy aceita apenas conexões locais; configure KAMY_MASTER_KEY no .env.
set -a; . ./.env; set +a
export KAMY_BROWSER_ENABLED=0
uvicorn app:app --host 127.0.0.1 --port 8000
\`\`\`

No navegador do Android, abra **http://127.0.0.1:8000** enquanto o Termux estiver executando. Para parar o servidor, use \`Ctrl+C\`.

### Debian via proot-distro no Termux

\`\`\`bash
proot-distro login debian
apt update
apt install -y git python3 python3-venv python3-pip build-essential libffi-dev libssl-dev
git clone https://github.com/stylesxzz/Kamy-Bot.git
cd Kamy-Bot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
# Edite .env e configure KAMY_MASTER_KEY.
set -a; . ./.env; set +a
export KAMY_BROWSER_ENABLED=0
python -m uvicorn app:app --host 127.0.0.1 --port 8000
\`\`\`

## Configuração

As variáveis são documentadas em \`.env.example\`. O Docker Compose carrega automaticamente o arquivo \`.env\`.

| Variável | Padrão | Descrição |
|---|---:|---|
| \`KAMY_PORT\` | \`8000\` | Porta publicada no host. |
| \`KAMY_BIND\` | \`127.0.0.1\` | Endereço de bind no host; manter localhost por padrão. |
| \`KAMY_BROWSER_ENABLED\` | \`1\` no Docker | Habilita Playwright no container. Use \`0\` no modo nativo/Termux. |
| \`KAMY_MASTER_KEY\` | vazio | Chave Fernet persistente para criptografar segredos/tokens OAuth. |

### Chave local para proteger credenciais

Gere uma chave Fernet e guarde-a em segurança. Ela criptografa chaves de API e tokens OAuth armazenados localmente:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copie o resultado para `KAMY_MASTER_KEY` no `.env`. Se perder essa chave, os segredos criptografados não poderão ser recuperados.
### Gerar a chave mestra OAuth

Com Python instalado:

\`\`\`bash
python -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
\`\`\`

Copie o resultado para \`KAMY_MASTER_KEY\` no arquivo \`.env\`. Preserve essa chave em local seguro e faça backup separado. Se ela for perdida ou alterada, os tokens criptografados existentes não poderão ser descriptografados.

Após alterar variáveis:

\`\`\`bash
docker compose up -d --force-recreate
\`\`\`

### Configurar NVIDIA NIM

1. Crie/obtenha uma chave no [NVIDIA API Catalog](https://build.nvidia.com/).
2. Abra a interface do Kamy Bot.
3. Crie um coworker ou edite a configuração de um agente.
4. Informe o modelo disponível no catálogo e a chave NVIDIA no campo próprio.
5. Salve e envie uma mensagem de teste.

Endpoint atualmente utilizado: \`https://integrate.api.nvidia.com/v1/chat/completions\`. A disponibilidade dos modelos e seus nomes pode mudar conforme o catálogo da NVIDIA.

## Extensões e estado real das integrações

A seção **Extensions** da interface agrupa os módulos:

| Módulo | Disponível nesta versão | Limite atual |
|---|---|---|
| Skills | Cadastro, revisão, habilitação, desativação e injeção automática de instruções aprovadas nos prompts dos coworkers. | Markdown declarativo apenas; não executa scripts. Limite de 8 Skills / 6.000 caracteres. |
| MCP | Descoberta de ferramentas via Streamable HTTP, grants individuais, validação de argumentos, ferramentas concedidas disponíveis aos coworkers e execução após aprovação. | Exige Streamable HTTP HTTPS e KAMY_MCP_ALLOWED_HOSTS; execução STDIO e OAuth de transporte MCP ainda não estão disponíveis. |
| Connect / OAuth | Cadastro de provedor, Authorization Code + PKCE S256, callback e armazenamento Fernet. | Configuração é específica por provedor; renovação/revogação e conectores prontos precisam ser adicionados. |
| Finance | Cadastro, listagem e aprovação de propostas. | Não consulta saldos universais e não envia ordens reais. A rota de execução retorna HTTP 501 intencionalmente. |
| Kamy Intel | Casos e evidências HTTPS. | Conectores automáticos para redes sociais e provedores de dados específicos ainda não estão implementados. |

O OAuth requer que o operador cadastre os endpoints oficiais, client ID, callback e escopos do provedor. O callback usado pela aplicação é:

\`\`\`text
https://SEU-DOMINIO/api/extensions/oauth/callback
\`\`\`

Em desenvolvimento local, use o endereço de callback que o provedor aceite e que corresponda exatamente à configuração informada na interface. Nunca compartilhe client secrets, access tokens ou a chave mestra.

## Segurança e implantação

- Docker Compose publica em \`127.0.0.1\` por padrão.
- Não altere \`KAMY_BIND\` para \`0.0.0.0\` em uma rede pública sem uma camada de autenticação, HTTPS, firewall e revisão de segurança.
- A aplicação não tem login nem conta administrativa. O acesso é limitado ao loopback da própria máquina.
- Não coloque chaves de API, senhas ou tokens no Git, em Issues ou em Skills.
- Revise conteúdo de Skills e origem de servidores MCP antes de cadastrá-los.
- Conceda o menor conjunto possível de escopos OAuth.
- Use apenas fontes públicas ou APIs com autorização no Kamy Intel.
- Operações financeiras reais permanecem desabilitadas.
- Faça backup regular do volume Docker e da chave mestra OAuth.

As allowlists e confirmações são controles da aplicação, não substitutos de isolamento de rede ou sandbox de execução. O runtime MCP aceita apenas hostnames exatos configurados em `KAMY_MCP_ALLOWED_HOSTS`, resolve DNS e rejeita endereços não públicos, não segue redirects e exige grant por ferramenta. A confirmação do usuário deve ser reservada a operações com efeitos externos ou financeiros. Mantenha o serviço em loopback e não publique diretamente a porta 8000 na Internet. As chaves de API dos coworkers e os segredos/tokens OAuth são criptografados em repouso quando `KAMY_MASTER_KEY` está configurada; preserve essa chave para manter acesso aos dados. O Kamy foi projetado para uso individual e local. Não o exponha diretamente à Internet: use VPN privada ou túnel seguro se precisar acessá-lo remotamente. A execução de ferramentas externas continua limitada por permissões, validação de argumentos e confirmação do usuário.

## Testes e validação local

\`\`\`bash
python -m pip install -r requirements.txt pytest
python -m compileall -q app.py extensions.py tests
pytest -q
node --check static/app.js
node --check static/extensions.js
docker compose config -q
\`\`\`

No Windows, execute os mesmos comandos em um ambiente com Python, Node.js e Docker Compose instalados. O CI do GitHub executa a suíte Python, checagem sintática JavaScript e validação do Compose em Python 3.11 e 3.12.

## Estrutura do repositório

\`\`\`text
Kamy-Bot/
├── app.py                    # Aplicação FastAPI e coworkers originais
├── extensions.py             # Skills, OAuth, MCP, Finance e Intel APIs\n├── security.py               # Restrição de acesso local e headers de segurança
├── requirements.txt          # Dependências do backend
├── requirements-browser.txt  # Dependências do navegador
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── start.sh
├── start.bat
├── assets/
│   ├── kamy-mascot.svg        # Mascote oficial
│   └── brand-palette.svg
├── static/
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   ├── extensions.js
│   └── extensions.css
├── tests/
└── .github/workflows/ci.yml
\`\`\`

## Solução de problemas

**A porta 8000 já está em uso**

Altere \`KAMY_PORT\` no \`.env\` para, por exemplo, \`8010\`, e recrie:

\`\`\`bash
docker compose up -d --force-recreate
\`\`\`

Abra então http://127.0.0.1:8010.

**O container não inicia**

\`\`\`bash
docker compose logs --tail=200 kamy-bot
docker compose ps
\`\`\`

**O navegador não funciona no modo nativo**

Playwright/Chromium é opcional. Defina \`KAMY_BROWSER_ENABLED=0\` no modo nativo/Termux. Para browser automation, use a imagem Docker fornecida.

**OAuth retorna erro de chave mestra**

Confira se \`KAMY_MASTER_KEY\` está preenchida com uma chave Fernet válida e se é exatamente a mesma usada quando os tokens foram armazenados. Não gere uma nova chave para substituir uma chave perdida.

**O chat está em Demo Mode ou não responde**

Configure uma chave NVIDIA válida no coworker, confirme o nome do modelo no catálogo e verifique os logs:

\`\`\`bash
docker compose logs -f kamy-bot
\`\`\`

## Licença

Distribuído sob a licença MIT. Consulte [LICENSE](LICENSE).

---

<div align="center">
  <strong>KAMY BOT</strong><br>
  Seus coworkers de IA. Suas ferramentas. Seu ambiente de trabalho.
</div>
