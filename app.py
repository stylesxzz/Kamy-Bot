import os, sqlite3, uuid, json, re
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
try:
 from playwright.async_api import async_playwright
except ImportError:
 async_playwright=None

ROOT=Path(__file__).parent
DATA=Path(os.getenv("KAMY_DATA_DIR","./data")); WORK=DATA/"workspaces"; DB=DATA/"kamy.sqlite3"
DATA.mkdir(parents=True,exist_ok=True); WORK.mkdir(parents=True,exist_ok=True)
NVIDIA_URL="https://integrate.api.nvidia.com/v1/chat/completions"
app=FastAPI(title="Kamy Bot",version="1.0.0")
app.mount("/assets",StaticFiles(directory=str(ROOT/"assets")),name="assets")
app.mount("/static",StaticFiles(directory=str(ROOT/"static")),name="static")
DEFAULT=[
 {"id":"nova","name":"NOVA","role":"Research coworker","description":"Researches approved websites and turns findings into concise notes.","domains":["example.com"],"tools":["browser.goto","browser.screenshot","file.write","file.read"]},
 {"id":"pixel","name":"PIXEL","role":"Developer coworker","description":"Creates and reads project files inside its private workspace.","domains":["example.com"],"tools":["file.write","file.read"]},
 {"id":"scout","name":"SCOUT","role":"Browser coworker","description":"Visits approved pages and captures browser evidence.","domains":["example.com"],"tools":["browser.goto","browser.screenshot","file.write","file.read"]}]
def now(): return datetime.now(timezone.utc).isoformat()
@contextmanager
def conn():
 c=sqlite3.connect(DB,timeout=15); c.row_factory=sqlite3.Row
 try:
  c.execute('PRAGMA busy_timeout=15000')
  yield c
  c.commit()
 except Exception:
  c.rollback(); raise
 finally:c.close()
def init():
 with conn() as c:
  c.executescript("""CREATE TABLE IF NOT EXISTS agents(id TEXT PRIMARY KEY,name TEXT,role TEXT,description TEXT,model TEXT,api_key TEXT,domains TEXT,tools TEXT,created TEXT);
  CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,agent_id TEXT,role TEXT,content TEXT,created TEXT);
  CREATE TABLE IF NOT EXISTS actions(id TEXT PRIMARY KEY,agent_id TEXT,kind TEXT,payload TEXT,status TEXT,decision TEXT,result TEXT,created TEXT,finished TEXT);""")
  if not c.execute("SELECT 1 FROM agents LIMIT 1").fetchone():
   for a in DEFAULT:c.execute("INSERT INTO agents VALUES(?,?,?,?,?,?,?,?,?)",(a["id"],a["name"],a["role"],a["description"],"meta/llama-3.3-70b-instruct",None,json.dumps(a["domains"]),json.dumps(a["tools"]),now()))
def agent(aid):
 with conn() as c:r=c.execute("SELECT * FROM agents WHERE id=?",(aid,)).fetchone()
 if not r:raise HTTPException(404,"Coworker not found")
 return r
def audit(aid,kind,payload,status="pending",decision=None,result=None,ident=None):
 with conn() as c:c.execute("INSERT INTO actions VALUES(?,?,?,?,?,?,?,?,?)",(ident or str(uuid.uuid4()),aid,kind,json.dumps(payload),status,decision,json.dumps(result) if result is not None else None,now(),now() if status!="pending" else None))
def safe_path(aid,rel):
 if rel.startswith("/") or ".." in Path(rel).parts:raise HTTPException(403,"Workspace boundary violation")
 base=(WORK/aid).resolve(); target=(base/rel).resolve()
 if target!=base and base not in target.parents:raise HTTPException(403,"Workspace boundary violation")
 return target
browser_engine=None; browser=None; contexts={}; pages={}
async def ensure_browser(aid):
 if not async_playwright or os.getenv('KAMY_BROWSER_ENABLED','1').lower() not in ('1','true','yes','on') or browser is None:
  raise HTTPException(503,'Browser tools are disabled on this installation.')
 if aid not in contexts:
  contexts[aid]=await browser.new_context(viewport={"width":1280,"height":800})
  pages[aid]=await contexts[aid].new_page()
@app.on_event("startup")
async def startup():
 global browser_engine,browser
 init()
 with conn() as c: ids=[r["id"] for r in c.execute("SELECT id FROM agents")]
 for aid in ids:(WORK/aid).mkdir(parents=True,exist_ok=True)
 browser_enabled=os.getenv('KAMY_BROWSER_ENABLED','1').lower() in ('1','true','yes','on')
 if browser_enabled and async_playwright:
  browser_engine=await async_playwright().start()
  browser=await browser_engine.chromium.launch(headless=True,args=['--no-sandbox'])
  for aid in ids: await ensure_browser(aid)
@app.on_event("shutdown")
async def shutdown():
 for context in list(contexts.values()): await context.close()
 contexts.clear(); pages.clear()
 if browser: await browser.close()
 if browser_engine: await browser_engine.stop()
@app.get("/",response_class=HTMLResponse)
def home():return (ROOT/"static/index.html").read_text()
@app.get("/api/health")
def health():return {"ok":True,"name":"Kamy Bot","provider":"NVIDIA NIM"}
def agent_json(r):return {"id":r["id"],"name":r["name"],"role":r["role"],"description":r["description"],"model":r["model"],"configured":bool(r["api_key"]),"domains":json.loads(r["domains"]),"tools":json.loads(r["tools"])}
@app.get("/api/agents")
def agents():
 with conn() as c:return [agent_json(r) for r in c.execute("SELECT * FROM agents ORDER BY created")]
class AgentIn(BaseModel):
 name:str=Field(min_length=2,max_length=40); role:str=Field(min_length=2,max_length=60); description:str=""; model:str="meta/llama-3.3-70b-instruct"; api_key:str|None=None
 domains:list[str]=Field(default_factory=lambda:["example.com"]); tools:list[str]=Field(default_factory=lambda:["browser.goto","browser.screenshot","file.write","file.read"])
@app.post("/api/agents")
def add_agent(b:AgentIn):
 if b.api_key and len(b.api_key)>512: raise HTTPException(400,'NVIDIA API key is too long')
 if any(not re.fullmatch(r'[a-zA-Z0-9.-]+',d) for d in b.domains): raise HTTPException(400,'Invalid domain')
 if any(t not in {'browser.goto','browser.screenshot','file.write','file.read'} for t in b.tools): raise HTTPException(400,'Unknown tool')
 aid=re.sub("[^a-z0-9-]","-",b.name.lower()).strip("-")[:24] or uuid.uuid4().hex[:8]
 if any(t not in {"browser.goto","browser.screenshot","file.write","file.read"} for t in b.tools):raise HTTPException(400,"Unknown tool")
 with conn() as c:
  if c.execute("SELECT 1 FROM agents WHERE id=?",(aid,)).fetchone():aid+="-"+uuid.uuid4().hex[:4]
  c.execute("INSERT INTO agents VALUES(?,?,?,?,?,?,?,?,?)",(aid,b.name,b.role,b.description,b.model,b.api_key,json.dumps(b.domains),json.dumps(b.tools),now()))
 (WORK/aid).mkdir(parents=True,exist_ok=True)
 return {"id":aid}
class Policy(BaseModel):
 domains:list[str]; tools:list[str]
@app.put("/api/agents/{aid}/policy")
def policy(aid:str,b:Policy):
 agent(aid); valid={"browser.goto","browser.screenshot","file.write","file.read"}
 if any(t not in valid for t in b.tools):raise HTTPException(400,"Unknown tool")
 if any(not re.fullmatch(r"[a-zA-Z0-9.-]+",d) for d in b.domains):raise HTTPException(400,"Invalid domain")
 with conn() as c:c.execute("UPDATE agents SET domains=?,tools=? WHERE id=?",(json.dumps(sorted(set(d.lower() for d in b.domains))),json.dumps(sorted(set(b.tools))),aid))
 audit(aid,"policy.update",b.model_dump(),"executed","owner",{"updated":True})
 return {"ok":True}
@app.get("/api/messages/{aid}")
def get_messages(aid:str):
 agent(aid)
 with conn() as c:return [dict(x) for x in c.execute("SELECT role,content,created FROM messages WHERE agent_id=? ORDER BY created",(aid,))]
class Chat(BaseModel):message:str=Field(min_length=1,max_length=4000)
@app.post("/api/chat/{aid}")
async def chat(aid:str,b:Chat):
 a=agent(aid); msg=b.message.strip()
 with conn() as c:
  c.execute("INSERT INTO messages VALUES(?,?,?,?,?)",(str(uuid.uuid4()),aid,"user",msg,now()))
  hist=[dict(x) for x in c.execute("SELECT role,content FROM messages WHERE agent_id=? ORDER BY created",(aid,))]
 reply="Demo mode ativo. Configure sua chave NVIDIA API para conversar com o modelo. Posso propor navegação e operações de arquivo, sempre aguardando sua aprovação."
 if a["api_key"]:
  try:
   async with httpx.AsyncClient(timeout=90) as client:
    r=await client.post(NVIDIA_URL,headers={"Authorization":"Bearer "+a["api_key"],"Content-Type":"application/json"},json={"model":a["model"],"messages":[{"role":"system","content":"Você é um coworker do Kamy Bot. Responda em português. Não afirme que realizou ferramentas; as ações precisam ser aprovadas pelo usuário."}]+hist,"temperature":0.5,"max_tokens":1200})
    r.raise_for_status();reply=r.json()["choices"][0]["message"]["content"]
  except Exception:reply="Falha na NVIDIA API. Confira a chave, o modelo e a disponibilidade do endpoint."
 with conn() as c:c.execute("INSERT INTO messages VALUES(?,?,?,?,?)",(str(uuid.uuid4()),aid,"assistant",reply,now()))
 u=re.search(r"https?://[^\s]+",msg)
 if u and any(x in msg.lower() for x in ["abra","abrir","visite","navegue","open"]):audit(aid,"browser.goto",{"url":u.group(0).rstrip(".,)")})
 f=re.search(r"(?:salve|crie|escreva)\s+(?:um arquivo\s+)?([\w./-]+\.[\w]+)",msg,re.I)
 if f:audit(aid,"file.write",{"path":f.group(1),"content":"Created by Kamy Bot coworker.\n"+msg})
 return {"reply":reply}
@app.get("/api/actions")
def actions(agent_id:str|None=None,limit:int=100):
 with conn() as c:
  q="SELECT * FROM actions"; args=[]
  if agent_id:q+=" WHERE agent_id=?";args.append(agent_id)
  q+=" ORDER BY created DESC LIMIT ?";args.append(min(max(limit,1),250))
  return [dict(x) for x in c.execute(q,args)]
@app.post("/api/actions/{ident}/decision")
async def decide(ident:str,b:dict):
 decision=b.get("decision")
 if decision not in ("approve","reject"):raise HTTPException(400,"Invalid decision")
 with conn() as c:r=c.execute("SELECT * FROM actions WHERE id=?",(ident,)).fetchone()
 if not r:raise HTTPException(404,"Action not found")
 if r["status"]!="pending":raise HTTPException(409,"Already decided")
 payload=json.loads(r["payload"]); a=agent(r["agent_id"])
 if decision=="reject":
  with conn() as c:c.execute("UPDATE actions SET status='rejected',decision=?,result=?,finished=? WHERE id=?",(decision,json.dumps({"rejected":True}),now(),ident))
  return {"status":"rejected"}
 try:
  tools=json.loads(a["tools"]); domains=json.loads(a["domains"]); kind=r["kind"]; result={}
  if kind not in tools:raise PermissionError("Tool not allowed")
  if kind=="browser.goto":
   p=urlparse(payload["url"]); host=(p.hostname or "").lower()
   if p.scheme not in ("http","https") or host not in domains or host in ("localhost","127.0.0.1","0.0.0.0") or host.endswith(".local"):raise PermissionError("Destination outside approved domain boundary")
   await ensure_browser(r["agent_id"]);await pages[r["agent_id"]].goto(payload["url"],wait_until="domcontentloaded",timeout=15000)
   result={"url":pages[r["agent_id"]].url,"title":await pages[r["agent_id"]].title()}
  elif kind=="file.write":
   p=safe_path(r["agent_id"],payload["path"]);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(payload.get("content",""),encoding="utf-8");result={"path":payload["path"],"bytes":p.stat().st_size}
  elif kind=="file.read":
   p=safe_path(r["agent_id"],payload["path"]);result={"path":payload["path"],"content":p.read_text(encoding="utf-8")[:10000]}
  elif kind=="browser.screenshot":
   await ensure_browser(r["agent_id"]);result={"screenshot":True}
   await pages[r["agent_id"]].screenshot(path=str(WORK/r["agent_id"]/"latest.png"))
  else:raise PermissionError("Unknown action")
  with conn() as c:c.execute("UPDATE actions SET status='executed',decision='approve',result=?,finished=? WHERE id=?",(json.dumps(result),now(),ident))
  return {"status":"executed","result":result}
 except Exception as e:
  with conn() as c:c.execute("UPDATE actions SET status='blocked',decision='approve',result=?,finished=? WHERE id=?",(json.dumps({"error":str(e)}),now(),ident))
  raise HTTPException(403,"Blocked by policy: "+str(e))
@app.get("/api/browser/{aid}/screenshot")
async def shot(aid:str):
 agent(aid);await ensure_browser(aid);return Response(await pages[aid].screenshot(type="png"),media_type="image/png")
@app.get("/api/workspace/{aid}")
def workspace(aid:str):
 agent(aid);return [{"path":str(p.relative_to(WORK/aid)),"bytes":p.stat().st_size} for p in (WORK/aid).rglob("*") if p.is_file()]

# Modular capability APIs; original coworker routes remain unchanged.
from extensions import router as extensions_router
app.include_router(extensions_router)
