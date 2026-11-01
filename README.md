<div align="center">
  <img src="assets/kamy-mascot.svg" width="132" alt="Mascote Kamy — estrela verde" />
  <h1>KAMY BOT</h1>
  <p><strong>Seu assistente de IA local em uma ilha flutuante.</strong></p>
  <p>Open source · Individual · Desktop · Local-first</p>
  <img src="assets/brand-palette.svg" width="100%" alt="Paleta Kamy Bot — Ivory, Frosted Mint, Malachite, Forest Green e Evergreen" />
  <p><a href="#instalação">Instalação</a> · <a href="#ilha-flutuante">Ilha flutuante</a> · <a href="#configuração-da-api">API</a> · <a href="#segurança-e-dados">Segurança</a></p>
</div>

---

## O que é

Kamy Bot é um aplicativo de desktop/local para uma única pessoa. Ele abre como uma pequena ilha flutuante que pode ficar sobre outras janelas. Quando você precisa de todas as ferramentas, expande para tela cheia.

**Não é SaaS, não é multiusuário, não conecta instalações e não possui painel administrativo ou camada de operador.** Seus agentes, conversas, credenciais, Skills, servidores MCP, conexões e arquivos pertencem à sua instalação local.

O backend usa Python/FastAPI em localhost. A janela desktop usa Electron; o navegador continua disponível como alternativa.

## Ilha flutuante

- **Janela compacta:** abre uma janela frameless, redimensionável e sempre no topo quando o sistema operacional permite.
- **Escolha do agente:** alterne entre NOVA, PIXEL, SCOUT e seus agentes personalizados diretamente no seletor da ilha.
- **Tela cheia:** expande a janela para acessar histórico, permissões, extensões, integrações e configurações.
- **Voz:** o microfone usa reconhecimento de fala do navegador em português brasileiro (pt-BR). A transcrição aparece no campo de mensagem para você revisar antes de enviar.
- **Atalho para voltar:** use o controle de recolher para retornar à ilha compacta.
- **Fallback:** quando o Electron não estiver instalado ou não for suportado, o launcher abre a interface local no navegador. Use --web para escolher o navegador explicitamente.

O reconhecimento de fala depende do suporte do Chromium e das permissões de microfone do sistema. Alguns mecanismos de reconhecimento podem precisar de conexão com a Internet. A voz é convertida em texto; o envio da mensagem continua sob seu controle.

**Linux/Wayland:** alguns compositores Wayland não permitem que aplicativos imponham a posição “sempre no topo”. O Kamy detecta Wayland e evita afirmar que o comportamento está garantido nessa sessão.

## Recursos

- **Agentes:** NOVA (pesquisa), PIXEL (desenvolvimento), SCOUT (navegação) e agentes personalizados, com conversas e workspaces locais separados.
- **NVIDIA NIM:** Chat Completions, modelo configurável, chave padrão e chaves individuais por agente.
- **Configurações:** aparência, escala de texto, alto contraste, espaçamento, redução de movimento, provedor, runtime e conexões.
- **Histórico de ações:** propostas, aprovações, rejeições, execuções e bloqueios.
- **Permissões:** ferramentas e domínios aprovados por agente; as políticas são revalidadas antes da execução.
- **Skills:** importar, revisar, ativar, desativar e remover instruções declarativas SKILL.md.
- **MCP:** servidores locais STDIO e Streamable HTTP, descoberta de ferramentas e execução com aprovação.
- **OAuth:** Authorization Code + PKCE para conexões HTTP MCP compatíveis. Segredos e tokens ficam criptografados localmente.
- **Finance / Binance:** cotações públicas, consulta privada de saldos e ordens de teste ou reais com confirmação explícita.
- **Kamy Intel:** casos locais e registro de evidências, fontes, URLs e datas observadas.

### Limites funcionais

- O chat com NVIDIA exige uma chave válida e um identificador de modelo suportado pela NVIDIA.
- O runtime nativo não habilita Playwright/Chromium headless; use --docker para o navegador de automação isolado.
- Servidores MCP STDIO executam programas na própria máquina, com as permissões do usuário local. Revise o comando e os argumentos.
- Skills são instruções em Markdown; o conteúdo importado não é executado como programa.
- Ordens reais da Binance podem causar perdas. Use Testnet primeiro e uma API key sem permissão de saque.
- Pesquisa automática na Internet depende de um MCP ou provedor de pesquisa que você configurar.

## Instalação

### Requisitos

- Node.js 18 ou superior.
- Python 3.11 ou superior.
- Conexão com a Internet na primeira execução, para baixar as dependências.
- Electron é instalado como dependência opcional do pacote. Se a plataforma não oferecer esse runtime, o Kamy abre no navegador.
- Docker Engine/Desktop somente para o modo de automação de navegador.

### Instalação rápida

Com o repositório clonado em uma pasta chamada Kamy-Bot, execute o comando a partir da pasta que contém esse diretório:

~~~bash
git clone https://github.com/stylesxzz/Kamy-Bot.git
npm exec --yes --package=./Kamy-Bot -- kamy-bot
~~~

O comando prepara automaticamente:

1. ~/.kamy-bot/app (ou o diretório informado por KAMY_HOME).
2. O ambiente virtual Python .venv.
3. O arquivo .env privado, sem substituir a chave já existente.
4. As dependências listadas em requirements.txt.
5. O banco SQLite e os workspaces locais.
6. O servidor FastAPI em 127.0.0.1.
7. A ilha flutuante Electron, se o runtime estiver disponível; caso contrário, abre o navegador.

O launcher preserva .env, .venv válido e dados locais ao atualizar os arquivos do app. Se o ambiente virtual estiver incompleto, somente .venv será recriado.

### Comandos

| Comando | Ação |
|---|---|
| npm exec --yes --package=./Kamy-Bot -- kamy-bot | Inicia a ilha flutuante (padrão) |
| npm exec --yes --package=./Kamy-Bot -- kamy-bot --web | Abre a interface no navegador |
| npm exec --yes --package=./Kamy-Bot -- kamy-bot --no-open | Inicia o servidor sem abrir uma janela |
| npm exec --yes --package=./Kamy-Bot -- kamy-bot --docker | Inicia com Docker e Playwright isolado |
| npm exec --yes --package=./Kamy-Bot -- kamy-bot --port 9000 | Usa outra porta local |
| npm exec --yes --package=./Kamy-Bot -- kamy-bot --setup-only | Prepara .venv e dependências sem iniciar o app |
| npm exec --yes --package=./Kamy-Bot -- kamy-bot --help | Mostra a ajuda |

Também é possível iniciar diretamente após clonar:

~~~bash
cd Kamy-Bot
node ./bin/kamy-bot.js
~~~

### Docker com navegador de automação

Em um computador com Docker instalado e iniciado:

~~~bash
npm exec --yes --package=./Kamy-Bot -- kamy-bot --docker
~~~

O modo Docker constrói a imagem com Playwright/Chromium e persiste o banco e os workspaces no volume kamy_data. O Docker não é instalado automaticamente pelo Kamy.

### Linux, Windows e macOS

Instale Node.js 18+ e Python 3.11+. Clone o repositório e execute o comando npm da instalação rápida. No Windows, o launcher usa py -3 quando disponível. No Linux, a ilha depende do suporte de janelas do ambiente gráfico.

### Android / Termux

Termux pode executar o backend local:

~~~bash
pkg update -y
pkg install -y nodejs-lts python git
git clone https://github.com/stylesxzz/Kamy-Bot.git
cd Kamy-Bot
node ./bin/kamy-bot.js --web
~~~

Em Termux sem uma sessão gráfica compatível com Electron, use --web e abra a interface no navegador. A ilha desktop nativa é destinada a ambientes com suporte a janelas de desktop.

## Configuração da API

Abra **Configurações → NVIDIA NIM padrão** e informe o identificador do modelo NVIDIA e sua NVIDIA API key.

Pressione **Salvar provedor**. O Kamy confirma a gravação no banco local e limpa o campo da chave depois da confirmação. A interface não recebe a chave de volta.

Você também pode definir uma chave individual por agente. Uma chave particular tem prioridade sobre a chave padrão.

### Persistência da chave mestra

O Kamy usa Fernet para criptografar as credenciais em repouso:

1. Se KAMY_MASTER_KEY estiver definida, ela é usada.
2. Caso contrário, o Kamy procura uma chave já existente no .env local.
3. Se nenhuma estiver disponível, cria uma chave estável em data/.master_key, com permissões de arquivo restritas ao usuário (0600 quando suportado).

A chave não é regenerada se o arquivo já existir. **Mantenha a chave mestra e a pasta de dados juntas e faça backup seguro.** Apagar ou substituir a chave pode tornar as credenciais antigas irrecuperáveis.

Se você já tem credenciais criptografadas, não apague o .env nem data/.master_key para “corrigir” uma falha de gravação.

## Dados locais

~~~text
~/.kamy-bot/
└── app/
    ├── .env                  # configurações locais e chave mestra, se definida
    ├── .venv/                # ambiente virtual Python
    ├── app.py                # backend FastAPI
    ├── security.py           # limites locais e chave criptográfica
    ├── desktop/              # janela Electron e preload seguro
    ├── static/               # ilha, interface, estilos e scripts
    ├── assets/               # marca e mascote SVG
    └── data/
        ├── .master_key       # chave mestra local gerada automaticamente, se necessária
        ├── kamy.sqlite3      # conversas, configurações e histórico
        └── workspaces/       # arquivos isolados por agente
~~~

KAMY_HOME altera o diretório de instalação. KAMY_DATA_DIR altera o local dos dados usado pelo backend.

## Segurança e dados

- O servidor escuta em 127.0.0.1 por padrão e rejeita solicitações remotas.
- Não exponha a porta local à Internet.
- Credenciais NVIDIA, OAuth e Binance são criptografadas com Fernet.
- Mantenha .env, data/.master_key, banco SQLite e workspaces privados.
- Dê aos agentes apenas as ferramentas MCP necessárias e revise cada execução.
- A aprovação não ignora os limites de workspace, domínio e ferramentas.
- O Electron usa contextIsolation, nodeIntegration: false e um preload restrito.

## Desenvolvimento e validação

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pytest -q
node --check bin/kamy-bot.js
node --check desktop/main.js
node --check desktop/preload.js
node --check static/app.js
node --check static/settings.js
node --check static/extensions.js
~~~

No Windows PowerShell, ative o ambiente com .venv\Scripts\Activate.ps1.

## Licença

Kamy Bot é distribuído sob a licença [MIT](LICENSE).
