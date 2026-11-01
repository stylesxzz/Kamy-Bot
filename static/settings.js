(()=>{"use strict";
const $=s=>document.querySelector(s),root=document.documentElement;
const csrf=()=>decodeURIComponent((document.cookie.split("; ").find(x=>x.startsWith("kamy_csrf="))||"kamy_csrf=").split("=")[1]||"");
async function request(path,options={}){
 const method=(options.method||"GET").toUpperCase(),headers={"Content-Type":"application/json",...(options.headers||{})};
 if(["POST","PUT","PATCH","DELETE"].includes(method))headers["X-CSRF-Token"]=csrf();
 const response=await fetch("/api"+path,{...options,method,headers,credentials:"same-origin"});
 const data=await response.json().catch(()=>({detail:"Resposta inválida do servidor."}));
 if(!response.ok)throw new Error(data.detail||"Não foi possível salvar a configuração.");
 return data;
}
function toast(message){const el=$("#toast");if(!el)return;el.textContent=message;el.classList.add("show");window.setTimeout(()=>el.classList.remove("show"),3200)}
const preferenceKey="kamy.local-ui.preferences";
function readPrefs(){try{return JSON.parse(localStorage.getItem(preferenceKey)||"{}")}catch{return {}}}
function applyPrefs(prefs){
 const scale=["1","1.08","1.16"].includes(String(prefs.scale))?String(prefs.scale):"1";
 root.style.setProperty("--ui-scale",scale);
 root.dataset.contrast=prefs.contrast?"high":"normal";
 root.dataset.density=prefs.compact?"compact":"comfortable";
 root.dataset.motion=prefs.reduceMotion?"reduce":"full";
 if($("#uiScale"))$("#uiScale").value=scale;
 if($("#uiContrast"))$("#uiContrast").checked=!!prefs.contrast;
 if($("#uiCompact"))$("#uiCompact").checked=!!prefs.compact;
 if($("#uiMotion"))$("#uiMotion").checked=!!prefs.reduceMotion;
}
function capturePrefs(){return {scale:$("#uiScale").value,contrast:$("#uiContrast").checked,compact:$("#uiCompact").checked,reduceMotion:$("#uiMotion").checked}}
function bindPrefs(){
 applyPrefs(readPrefs());
 $("#saveUi").onclick=()=>{const p=capturePrefs();localStorage.setItem(preferenceKey,JSON.stringify(p));applyPrefs(p);toast("Preferências visuais salvas neste navegador.")};
 $("#resetUi").onclick=()=>{localStorage.removeItem(preferenceKey);applyPrefs({});toast("Aparência restaurada.")};
}
function runtimeRows(s){
 const rows=[["Modo",s.runtime_mode],["Endereço",s.bind_host+":"+s.port],["Pasta de dados",s.data_dir],["Chave mestra",s.master_key_configured?"Configurada":"Ausente"],["NVIDIA default",s.default_api_key_configured?"Chave local criptografada":"Não configurada"],["Browser",s.browser_running?"Ativo":(s.browser_enabled?(s.browser_available?"Habilitado, aguardando runtime":"Playwright ausente"):"Desabilitado")]];
 return rows.map(([k,v])=>'<div class="runtime-row"><span>'+k+'</span><b>'+String(v??"—").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]))+'</b></div>').join("");
}
function agentCards(agents){
 const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
 $("#agentProviderCards").innerHTML=agents.map(a=>'<form class="agent-provider-card" data-agent-provider="'+esc(a.id)+'"><h3>'+esc(a.name)+'</h3><p>'+esc(a.role)+' · '+(a.configured?(a.uses_default_provider?"Using default key":"Private key configured"):"Demo mode")+'</p><label class="settings-field">Model<input name="model" value="'+esc(a.model)+'" required maxlength="160"></label><label class="settings-field">Private NVIDIA API key<input name="api_key" type="password" autocomplete="new-password" placeholder="Leave blank to keep current"></label><label class="settings-toggle"><input name="clear_api_key" type="checkbox"><span><b>Remove this coworker key</b><small>Use the global key instead, when configured.</small></span></label><button class="secondary-btn">Save coworker</button></form>').join("")||"<p>No coworkers configured.</p>";
 document.querySelectorAll("[data-agent-provider]").forEach(form=>form.addEventListener("submit",async event=>{
  event.preventDefault();const data=new FormData(form),body={model:String(data.get("model")||"").trim(),api_key:String(data.get("api_key")||"").trim()||null,clear_api_key:data.get("clear_api_key")==="on"};
  try{const result=await request("/agents/"+encodeURIComponent(form.dataset.agentProvider)+"/provider",{method:"PUT",body:JSON.stringify(body)});if(body.api_key&&!result.configured)throw new Error("A chave do coworker não foi confirmada pelo servidor.");toast(body.api_key?"Chave do coworker salva e criptografada.":"Configuração do coworker salva.");await render()}catch(error){toast(error.message)}
 }));
}
async function render(){
 bindPrefs();
 try{
  const [settings,agents]=await Promise.all([request("/settings"),request("/agents")]);
  $("#defaultModel").value=settings.default_model;
  $("#providerState").textContent=settings.default_api_key_configured?"Chave padrão salva · criptografada":"Nenhuma chave padrão salva";
  $("#runtimeInfo").innerHTML=runtimeRows(settings);
  agentCards(agents);$("#clearDefaultKey").checked=false;$("#defaultApiKey").value="";
 }catch(error){$("#providerState").textContent="Falha ao ler configurações";$("#runtimeInfo").textContent=error.message;toast(error.message)}
}
$("#defaultProviderForm").addEventListener("submit",async event=>{
 event.preventDefault();
 const body={default_model:$("#defaultModel").value.trim(),default_api_key:$("#defaultApiKey").value.trim()||null,clear_default_api_key:$("#clearDefaultKey").checked,apply_default_model:$("#applyModelAll").checked};
 try{
  const keyWasProvided=Boolean(body.default_api_key);
  const result=await request("/settings",{method:"PUT",body:JSON.stringify(body)});
  if(keyWasProvided&&!result.default_api_key_configured)throw new Error("O servidor não confirmou a gravação da chave NVIDIA.");
  $("#defaultApiKey").value="";$("#clearDefaultKey").checked=false;$("#applyModelAll").checked=false;
  toast(keyWasProvided?"Chave NVIDIA salva e criptografada.":(body.clear_default_api_key?"Chave NVIDIA removida.":"Configurações do provedor salvas."));await render();
 }catch(error){toast(error.message)}
});
document.addEventListener("click",event=>{const button=event.target.closest("[data-open-view]");if(button)document.querySelector('[data-view="'+button.dataset.openView+'"]')?.click()});
window.KamySettings={render};
})();