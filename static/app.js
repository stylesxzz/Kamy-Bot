"use strict";

const $ = selector => document.querySelector(selector);
const desktop = window.kamyDesktop?.isDesktop ? window.kamyDesktop : null;
let team = [];
let active = null;
let events = [];
let currentView = "home";

const esc = value => String(value ?? "").replace(/[&<>"']/g, character => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}[character]));

async function api(url, options = {}) {
  const csrfCookie = document.cookie.split("; ").find(item => item.startsWith("kamy_csrf="))?.split("=")[1] || "";
  const method = (options.method || "GET").toUpperCase();
  const headers = {"Content-Type": "application/json", ...(options.headers || {})};
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    try { headers["X-CSRF-Token"] = decodeURIComponent(csrfCookie); }
    catch { headers["X-CSRF-Token"] = csrfCookie; }
  }
  const response = await fetch(url, {...options, method, headers, credentials: "same-origin"});
  const data = await response.json().catch(() => ({detail: "Resposta inválida do servidor."}));
  if (!response.ok) throw new Error(data.detail || "A solicitação falhou.");
  return data;
}

function toast(message) {
  const element = $("#toast");
  if (!element) return;
  element.textContent = message;
  element.classList.add("show");
  window.setTimeout(() => element.classList.remove("show"), 3200);
}

function applyDesktopMode(expanded) {
  if (!desktop) return;
  document.body.classList.add("desktop-app");
  document.body.classList.toggle("island-mode", !expanded);
  document.body.classList.toggle("expanded-mode", Boolean(expanded));
  const expand = $("#desktopExpand");
  const collapse = $("#desktopCollapse");
  if (expand) expand.hidden = Boolean(expanded);
  if (collapse) collapse.hidden = !expanded;
}

async function toggleDesktopMode(expanded) {
  if (!desktop) return;
  try {
    const actual = await desktop.setExpanded(Boolean(expanded));
    applyDesktopMode(Boolean(actual));
  } catch (error) {
    toast("Não foi possível alterar a janela: " + error.message);
  }
}

function renderTeam() {
  $("#agentList").innerHTML = team.map(agent =>
    '<div class="agent-link ' + (agent.id === active ? "active" : "") +
    '" data-agent="' + esc(agent.id) + '"><i></i>' + esc(agent.name) + "</div>"
  ).join("");

  document.querySelectorAll("[data-agent]").forEach(element => {
    element.onclick = () => selectAgent(element.dataset.agent);
  });

  const selector = $("#desktopAgentSelect");
  if (selector) {
    selector.innerHTML = team.map(agent =>
      '<option value="' + esc(agent.id) + '">' + esc(agent.name) + " · " +
      esc(agent.role) + "</option>"
    ).join("");
    selector.value = active || team[0]?.id || "";
  }
  $("#count").textContent = team.length + " AGENTES";
}

function renderCards() {
  $("#cards").innerHTML = team.map(agent =>
    '<article class="card ' + (agent.id === active ? "selected" : "") +
    '" data-card="' + esc(agent.id) + '">' +
      '<div class="cardtop"><div class="symbol">' + esc(agent.name[0]) +
      '</div><span class="ready">● ' + (agent.configured ? "NVIDIA CONECTADO" : "MODO DEMO") +
      "</span></div>" +
      "<h3>" + esc(agent.name) + "</h3>" +
      '<div class="role">' + esc(agent.role.toUpperCase()) + "</div>" +
      "<p>" + esc(agent.description) + "</p>" +
      '<div class="cardfoot"><span>' + agent.tools.length + " FERRAMENTAS</span><span>" +
      esc(agent.model) + " →</span></div></article>"
  ).join("");

  document.querySelectorAll("[data-card]").forEach(element => {
    element.onclick = () => selectAgent(element.dataset.card);
  });
}

async function selectAgent(id) {
  const agent = team.find(item => item.id === id);
  if (!agent) return;
  active = id;
  try { localStorage.setItem("kamy.active-agent", id); } catch { /* Storage can be disabled. */ }
  renderTeam();
  renderCards();
  $("#agentAvatar").textContent = agent.name[0];
  $("#agentName").textContent = agent.name;
  $("#agentRole").textContent = agent.role;
  await loadMessages();
  renderActivity();
  refreshShot();
}

async function loadMessages() {
  if (!active) return;
  const messages = await api("/api/messages/" + encodeURIComponent(active));
  $("#messages").innerHTML = messages.map(message =>
    '<div class="msg ' + (message.role === "user" ? "user" : "assistant") + '">' +
      "<small>" + (message.role === "user" ? "VOCÊ" : esc(team.find(item => item.id === active)?.name)) +
      "</small>" + esc(message.content) + "</div>"
  ).join("");
  $("#messages").scrollTop = $("#messages").scrollHeight;
}

async function sendMessage(message) {
  if (!active || !message.trim()) return;
  await api("/api/chat/" + encodeURIComponent(active), {
    method: "POST",
    body: JSON.stringify({message: message.trim()})
  });
  await loadMessages();
  await refreshEvents();
}

$("#chatForm").addEventListener("submit", async event => {
  event.preventDefault();
  const input = $("#chatInput");
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  try {
    await sendMessage(message);
  } catch (error) {
    input.value = message;
    toast(error.message);
  }
});

function setupVoiceInput() {
  const button = $("#voiceButton");
  const input = $("#chatInput");
  if (!button || !input) return;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    button.disabled = true;
    button.title = "Reconhecimento de voz não disponível neste ambiente.";
    return;
  }

  let recognition = null;
  let recording = false;
  button.addEventListener("click", () => {
    if (recording) {
      recognition?.stop();
      return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = "pt-BR";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      recording = true;
      button.classList.add("recording");
      button.textContent = "■";
      button.title = "Parar gravação";
      input.placeholder = "Estou ouvindo…";
    };

    recognition.onresult = event => {
      let transcript = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        transcript += event.results[index][0].transcript;
      }
      if (transcript.trim()) input.value = transcript.trim();
    };

    recognition.onerror = event => {
      const messages = {
        "not-allowed": "Permita o acesso ao microfone nas configurações do sistema.",
        "no-speech": "Não detectei fala. Tente novamente.",
        "audio-capture": "Nenhum microfone foi encontrado."
      };
      toast(messages[event.error] || "Falha no reconhecimento de voz: " + event.error);
    };

    recognition.onend = () => {
      recording = false;
      button.classList.remove("recording");
      button.textContent = "🎙";
      button.title = "Ditar mensagem em português";
      input.placeholder = "Escreva ou dite uma mensagem...";
      if (input.value.trim()) input.focus();
    };

    try { recognition.start(); }
    catch (error) { toast("Não foi possível iniciar o microfone: " + error.message); }
  });
}

async function refreshEvents() {
  events = await api("/api/actions?limit=150");
  renderActivity();
  renderPending();
}

function renderActivity() {
  const items = events.filter(item => item.agent_id === active).slice(0, 5);
  $("#recent").innerHTML = items.length ? items.map(item =>
    '<div class="activity-row"><span>✧</span><span><b>' + esc(item.kind) +
    '</b><small>' + new Date(item.created).toLocaleString("pt-BR") +
    '</small></span><span class="status ' + esc(item.status) + '">' +
    esc(item.status.toUpperCase()) + "</span></div>"
  ).join("") : '<div class="activity-row">Nenhuma ação registrada.</div>';
}

function renderPending() {
  const items = events.filter(item => item.agent_id === active && item.status === "pending");
  $("#pending").innerHTML = items.map(item =>
    '<div class="pending"><strong>⚠ APROVAÇÃO NECESSÁRIA · ' + esc(item.kind) +
    "</strong><p>" + esc(item.payload) + '</p><button class="approve" data-yes="' +
    esc(item.id) + '">Aprovar</button><button class="reject" data-no="' +
    esc(item.id) + '">Rejeitar</button></div>'
  ).join("");

  document.querySelectorAll("[data-yes]").forEach(button => {
    button.onclick = () => decide(button.dataset.yes, "approve");
  });
  document.querySelectorAll("[data-no]").forEach(button => {
    button.onclick = () => decide(button.dataset.no, "reject");
  });
}

async function decide(id, decision) {
  try {
    await api("/api/actions/" + encodeURIComponent(id) + "/decision", {
      method: "POST",
      body: JSON.stringify({decision})
    });
    toast(decision === "approve" ? "Ação aprovada." : "Ação rejeitada.");
    await refreshEvents();
    refreshShot();
  } catch (error) {
    toast(error.message);
    await refreshEvents();
  }
}

function refreshShot() {
  if (!active) return;
  $("#screenshot").src = "/api/browser/" + encodeURIComponent(active) +
    "/screenshot?t=" + Date.now();
  const lastNavigation = events.find(item =>
    item.agent_id === active && item.kind === "browser.goto" && item.status === "executed"
  );
  if (lastNavigation) {
    try { $("#browserUrl").textContent = JSON.parse(lastNavigation.result).url; }
    catch { /* Invalid audit data is ignored. */ }
  }
}

$("#refreshShot").onclick = refreshShot;

async function audit() {
  events = await api("/api/actions?limit=250");
  $("#auditRows").innerHTML = events.map(item =>
    "<tr><td><code>" + esc(item.kind) + "</code></td><td>" +
    esc(team.find(agent => agent.id === item.agent_id)?.name || item.agent_id) +
    "</td><td>" + esc(item.payload) + '</td><td><span class="status ' +
    esc(item.status) + '">' + esc(item.status.toUpperCase()) +
    "</span></td><td>" + new Date(item.created).toLocaleString("pt-BR") + "</td></tr>"
  ).join("") || '<tr><td colspan="5">Nenhuma ação registrada.</td></tr>';
}

$("#reloadAudit").onclick = () => audit().catch(error => toast(error.message));

function renderPolicies() {
  $("#policies").innerHTML = team.map(agent =>
    '<div class="policy-card"><h3>' + esc(agent.name) + "</h3><p>" + esc(agent.role) +
    '</p><div class="policy-label">FERRAMENTAS PERMITIDAS</div><div class="checks">' +
    ["browser.goto", "browser.screenshot", "file.write", "file.read"].map(tool =>
      '<label><input type="checkbox" data-tool="' + tool + '" data-for="' +
      esc(agent.id) + '" ' + (agent.tools.includes(tool) ? "checked" : "") + "> " +
      tool + "</label>"
    ).join("") +
    '</div><div class="policy-label">DOMÍNIOS APROVADOS</div><textarea data-domains="' +
    esc(agent.id) + '">' + esc(agent.domains.join(", ")) +
    '</textarea><button data-save="' + esc(agent.id) + '">Salvar política</button></div>'
  ).join("");

  document.querySelectorAll("[data-save]").forEach(button => {
    button.onclick = async () => {
      const id = button.dataset.save;
      const domains = $('[data-domains="' + id + '"]').value
        .split(/[\n,]+/).map(value => value.trim()).filter(Boolean);
      const tools = [...document.querySelectorAll('[data-for="' + id + '"]:checked')]
        .map(element => element.dataset.tool);
      try {
        await api("/api/agents/" + encodeURIComponent(id) + "/policy", {
          method: "PUT",
          body: JSON.stringify({domains, tools})
        });
        team = await api("/api/agents");
        renderPolicies();
        renderTeam();
        renderCards();
        toast("Política salva e registrada.");
      } catch (error) { toast(error.message); }
    };
  });
}

function show(view) {
  currentView = view;
  ["home", "audit", "policy", "extensions", "settings"].forEach(name => {
    $("#" + name).classList.toggle("hidden", name !== view);
  });
  document.querySelectorAll(".nav").forEach(element => {
    element.classList.toggle("active", element.dataset.view === view);
  });
  $("#crumb").textContent = {
    home: "Conversas", audit: "Histórico", policy: "Permissões",
    extensions: "Extensões", settings: "Configurações"
  }[view] || view;
  if (view === "audit") audit().catch(error => toast(error.message));
  if (view === "policy") renderPolicies();
  if (view === "settings") window.KamySettings?.render();
}

document.querySelectorAll("[data-view]").forEach(element => {
  element.onclick = () => show(element.dataset.view);
});
document.querySelectorAll("[data-jump]").forEach(element => {
  element.onclick = () => show(element.dataset.jump);
});

function bindModal() {
  const modal = $("#modal");
  const toggle = visible => modal.classList.toggle("hidden", !visible);
  $("#addAgent").onclick = $("#heroAdd").onclick = () => toggle(true);
  $("#close").onclick = () => toggle(false);
  modal.onclick = event => { if (event.target.id === "modal") toggle(false); };

  $("#agentForm").onsubmit = async event => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target));
    data.domains = data.domains.split(",").map(value => value.trim()).filter(Boolean);
    data.tools = ["browser.goto", "browser.screenshot", "file.write", "file.read"];
    try {
      const result = await api("/api/agents", {
        method: "POST",
        body: JSON.stringify(data)
      });
      toggle(false);
      event.target.reset();
      team = await api("/api/agents");
      renderTeam();
      renderCards();
      renderPolicies();
      await selectAgent(result.id);
      toast("Agente criado.");
    } catch (error) { toast(error.message); }
  };
}

async function init() {
  if (desktop) {
    applyDesktopMode(false);
    $("#desktopExpand").onclick = () => toggleDesktopMode(true);
    $("#desktopCollapse").onclick = () => toggleDesktopMode(false);
    $("#desktopQuit").onclick = () => desktop.quit();
    $("#desktopAgentSelect").onchange = event => selectAgent(event.target.value);
    desktop.onModeChange?.(detail => applyDesktopMode(Boolean(detail?.expanded)));
  }

  setupVoiceInput();
  bindModal();

  team = await api("/api/agents");
  try {
    const saved = localStorage.getItem("kamy.active-agent");
    if (saved && team.some(agent => agent.id === saved)) active = saved;
  } catch { /* Optional local preference. */ }

  renderTeam();
  renderCards();
  renderPolicies();
  show("home");
  await selectAgent(active || team[0]?.id);
  await refreshEvents();
  window.setInterval(() => refreshEvents().catch(() => {}), 8000);
}

init().catch(error => toast(error.message));
