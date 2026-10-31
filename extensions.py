"""Kamy Bot extension control plane. Downloaded skill code, arbitrary MCP commands and financial orders are never executed automatically."""
import base64, hashlib, json, os, secrets, sqlite3, time, uuid
from pathlib import Path
from urllib.parse import urlencode, urlparse
import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

DATA=Path(os.getenv("KAMY_DATA_DIR","./data")); DATA.mkdir(parents=True,exist_ok=True)
DB=DATA/"kamy_extensions.sqlite3"
router=APIRouter(prefix="/api/extensions",tags=["Kamy Extensions"])
def db():
 c=sqlite3.connect(DB,timeout=15); c.row_factory=sqlite3.Row; c.execute("PRAGMA busy_timeout=15000"); return c
def init_db():
 with db() as c:
  c.executescript("""
  CREATE TABLE IF NOT EXISTS skills(id TEXT PRIMARY KEY,name TEXT,description TEXT,content TEXT,source TEXT,status TEXT,created REAL);
  CREATE TABLE IF NOT EXISTS mcp_servers(id TEXT PRIMARY KEY,name TEXT,transport TEXT,url TEXT,command TEXT,args TEXT,status TEXT,created REAL);
  CREATE TABLE IF NOT EXISTS oauth_providers(id TEXT PRIMARY KEY,name TEXT,authorization_url TEXT,token_url TEXT,client_id TEXT,client_secret TEXT,redirect_uri TEXT,scopes TEXT,created REAL);
  CREATE TABLE IF NOT EXISTS oauth_states(state TEXT PRIMARY KEY,provider_id TEXT,verifier TEXT,expires REAL,created REAL);
  CREATE TABLE IF NOT EXISTS oauth_tokens(provider_id TEXT PRIMARY KEY,access_token TEXT,refresh_token TEXT,token_type TEXT,scope TEXT,expires_at REAL,updated REAL);
  CREATE TABLE IF NOT EXISTS order_proposals(id TEXT PRIMARY KEY,provider_id TEXT,asset TEXT,side TEXT,quantity REAL,order_type TEXT,limit_price REAL,status TEXT,created REAL,decision_at REAL);
  CREATE TABLE IF NOT EXISTS intel_cases(id TEXT PRIMARY KEY,query TEXT,purpose TEXT,status TEXT,created REAL);
  CREATE TABLE IF NOT EXISTS intel_evidence(id TEXT PRIMARY KEY,case_id TEXT,url TEXT,title TEXT,snippet TEXT,observed_at TEXT,source_type TEXT,created REAL);
  """)
init_db()
def cipher():
 key=os.getenv("KAMY_MASTER_KEY","").strip()
 if not key: raise HTTPException(503,"Configure KAMY_MASTER_KEY with a valid Fernet key before storing OAuth secrets or tokens.")
 try: return Fernet(key.encode())
 except Exception: raise HTTPException(503,"KAMY_MASTER_KEY inválida. Gere uma chave Fernet válida.")
def seal(v): return cipher().encrypt(v.encode()).decode() if v else None
def unseal(v):
 if not v:return None
 try:return cipher().decrypt(v.encode()).decode()
 except InvalidToken:raise HTTPException(503,"Falha ao descriptografar credenciais; verifique KAMY_MASTER_KEY.")
def valid_https(v,label):
 p=urlparse(v)
 if p.scheme!="https" or not p.hostname or p.username or p.password:raise HTTPException(400,f"{label} deve ser uma URL HTTPS válida.")
 return v

class SkillIn(BaseModel):
 name:str=Field(min_length=2,max_length=80); description:str=Field(default="",max_length=500); content:str=Field(min_length=1,max_length=50000); source:str=Field(default="manual",max_length=500)
@router.get("/status")
def status():
 with db() as c:
  return {"skills":[dict(x) for x in c.execute("SELECT status,COUNT(*) n FROM skills GROUP BY status")],"mcp_servers":[dict(x) for x in c.execute("SELECT status,COUNT(*) n FROM mcp_servers GROUP BY status")],"oauth_providers":c.execute("SELECT COUNT(*) FROM oauth_providers").fetchone()[0],"order_proposals":[dict(x) for x in c.execute("SELECT status,COUNT(*) n FROM order_proposals GROUP BY status")],"intel_cases":c.execute("SELECT COUNT(*) FROM intel_cases").fetchone()[0],"master_key_configured":bool(os.getenv("KAMY_MASTER_KEY"))}
@router.get("/skills")
def skills():
 with db() as c:return [dict(x) for x in c.execute("SELECT id,name,description,source,status,created FROM skills ORDER BY created DESC")]
@router.post("/skills")
def add_skill(b:SkillIn):
 # Skills are declarative Markdown only; reject obvious executable payloads.
 fences=chr(96)*3
 if "<script" in b.content.lower() or fences+"python" in b.content.lower() or fences+"bash" in b.content.lower() or fences+"sh" in b.content.lower():raise HTTPException(400,"Skill contém código executável. O instalador aceita instruções declarativas revisáveis.")
 ident=str(uuid.uuid4())
 with db() as c:c.execute("INSERT INTO skills VALUES(?,?,?,?,?,?,?)",(ident,b.name,b.description,b.content,b.source,"pending_review",time.time()))
 return {"id":ident,"status":"pending_review"}
@router.post("/skills/{sid}/approve")
def approve_skill(sid:str):
 with db() as c:
  cur=c.execute("UPDATE skills SET status='enabled' WHERE id=? AND status='pending_review'",(sid,))
  if not cur.rowcount:raise HTTPException(404,"Skill pendente não encontrada.")
 return {"id":sid,"status":"enabled"}
@router.post("/skills/{sid}/disable")
def disable_skill(sid:str):
 with db() as c:
  cur=c.execute("UPDATE skills SET status='disabled' WHERE id=?",(sid,))
  if not cur.rowcount:raise HTTPException(404,"Skill não encontrada.")
 return {"id":sid,"status":"disabled"}

class MCPIn(BaseModel):
 name:str=Field(min_length=2,max_length=80); transport:str=Field(pattern="^(streamable-http|sse|stdio)$"); url:str|None=None; command:str|None=None; args:list[str]=Field(default_factory=list)
@router.get("/mcp")
def mcp_list():
 with db() as c:return [dict(x) for x in c.execute("SELECT id,name,transport,url,command,args,status,created FROM mcp_servers ORDER BY created DESC")]
@router.post("/mcp")
def mcp_add(b:MCPIn):
 if b.transport in ("streamable-http","sse"):
  if not b.url:raise HTTPException(400,"Informe a URL do MCP.")
  p=urlparse(b.url)
  if p.scheme not in ("https","http") or not p.hostname or p.username or p.password:raise HTTPException(400,"URL MCP inválida.")
  if p.scheme!="https" and p.hostname not in ("localhost","127.0.0.1","::1"):raise HTTPException(400,"MCP remoto exige HTTPS.")
  command=None
 else:
  if not b.command or len(b.command)>200:raise HTTPException(400,"Informe o executável MCP local.")
  command=b.command # stored only; never launched by this API
 ident=str(uuid.uuid4())
 with db() as c:c.execute("INSERT INTO mcp_servers VALUES(?,?,?,?,?,?,?,?)",(ident,b.name,b.transport,b.url,command,json.dumps(b.args),"registered_unverified",time.time()))
 return {"id":ident,"status":"registered_unverified","message":"Registrado, não executado. Revise origem e permissões antes de habilitar."}
@router.post("/mcp/{sid}/disable")
def mcp_disable(sid:str):
 with db() as c:
  cur=c.execute("UPDATE mcp_servers SET status='disabled' WHERE id=?",(sid,))
  if not cur.rowcount:raise HTTPException(404,"MCP não encontrado.")
 return {"id":sid,"status":"disabled"}

class OAuthIn(BaseModel):
 name:str=Field(min_length=2,max_length=80); authorization_url:str; token_url:str; client_id:str=Field(min_length=1,max_length=500); client_secret:str|None=None; redirect_uri:str; scopes:list[str]=Field(default_factory=list)
@router.get("/oauth/providers")
def oauth_providers():
 with db() as c:return [dict(x) for x in c.execute("SELECT id,name,authorization_url,token_url,client_id,redirect_uri,scopes,created FROM oauth_providers")]
@router.post("/oauth/providers")
def oauth_add(b:OAuthIn):
 for v,n in ((b.authorization_url,"authorization_url"),(b.token_url,"token_url"),(b.redirect_uri,"redirect_uri")):valid_https(v,n)
 ident=str(uuid.uuid4())
 with db() as c:c.execute("INSERT INTO oauth_providers VALUES(?,?,?,?,?,?,?,?,?)",(ident,b.name,b.authorization_url,b.token_url,b.client_id,seal(b.client_secret),b.redirect_uri,json.dumps(b.scopes),time.time()))
 return {"id":ident,"name":b.name,"status":"configured"}
@router.delete("/oauth/providers/{pid}")
def oauth_delete(pid:str):
 with db() as c:
  c.execute("DELETE FROM oauth_tokens WHERE provider_id=?",(pid,));c.execute("DELETE FROM oauth_states WHERE provider_id=?",(pid,));cur=c.execute("DELETE FROM oauth_providers WHERE id=?",(pid,))
  if not cur.rowcount:raise HTTPException(404,"OAuth provider não encontrado.")
 return {"deleted":True}
@router.post("/oauth/{pid}/start")
def oauth_start(pid:str):
 with db() as c:p=c.execute("SELECT * FROM oauth_providers WHERE id=?",(pid,)).fetchone()
 if not p:raise HTTPException(404,"OAuth provider não encontrado.")
 state=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(64);challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
 with db() as c:c.execute("INSERT INTO oauth_states VALUES(?,?,?,?,?)",(state,pid,verifier,time.time()+600,time.time()))
 params={"response_type":"code","client_id":p["client_id"],"redirect_uri":p["redirect_uri"],"scope":" ".join(json.loads(p["scopes"])),"state":state,"code_challenge":challenge,"code_challenge_method":"S256"}
 return {"authorization_url":p["authorization_url"]+"?"+urlencode(params),"state_expires_in":600,"pkce":"S256"}
@router.get("/oauth/callback")
async def oauth_callback(code:str=Query(min_length=1),state:str=Query(min_length=16)):
 with db() as c:
  s=c.execute("SELECT * FROM oauth_states WHERE state=?",(state,)).fetchone()
  if not s or s["expires"]<time.time():
   if s:c.execute("DELETE FROM oauth_states WHERE state=?",(state,))
   raise HTTPException(400,"OAuth state inválido ou expirado.")
  p=c.execute("SELECT * FROM oauth_providers WHERE id=?",(s["provider_id"],)).fetchone();c.execute("DELETE FROM oauth_states WHERE state=?",(state,))
 data={"grant_type":"authorization_code","code":code,"redirect_uri":p["redirect_uri"],"client_id":p["client_id"],"code_verifier":s["verifier"]}
 secret=unseal(p["client_secret"]);auth=(p["client_id"],secret) if secret else None
 try:
  async with httpx.AsyncClient(timeout=20,follow_redirects=False) as client:r=await client.post(p["token_url"],data=data,auth=auth,headers={"Accept":"application/json"})
  r.raise_for_status();token=r.json()
 except Exception:raise HTTPException(502,"Falha na troca do código OAuth; confira endpoint e credenciais.")
 if not token.get("access_token"):raise HTTPException(502,"Provedor não retornou access_token.")
 with db() as c:c.execute("INSERT OR REPLACE INTO oauth_tokens VALUES(?,?,?,?,?,?,?)",(p["id"],seal(token["access_token"]),seal(token.get("refresh_token")),token.get("token_type","Bearer"),token.get("scope",""),time.time()+int(token.get("expires_in",3600)),time.time()))
 return {"connected":True,"provider":p["name"],"message":"Tokens armazenados criptografados."}
@router.get("/oauth/connections")
def oauth_connections():
 with db() as c:return [{"provider_id":x["provider_id"],"token_type":x["token_type"],"scope":x["scope"],"expires_at":x["expires_at"],"connected":True} for x in c.execute("SELECT * FROM oauth_tokens")]

class OrderIn(BaseModel):
 provider_id:str; asset:str=Field(min_length=1,max_length=40); side:str=Field(pattern="^(buy|sell)$"); quantity:float=Field(gt=0,le=100000000); order_type:str=Field(default="market",pattern="^(market|limit)$"); limit_price:float|None=Field(default=None,gt=0)
@router.post("/finance/order-proposals")
def order_propose(b:OrderIn):
 if b.order_type=="limit" and b.limit_price is None:raise HTTPException(400,"Ordem limitada exige limit_price.")
 with db() as c:
  if not c.execute("SELECT 1 FROM oauth_providers WHERE id=?",(b.provider_id,)).fetchone():raise HTTPException(404,"Provedor financeiro não cadastrado.")
 ident=str(uuid.uuid4())
 with db() as c:c.execute("INSERT INTO order_proposals VALUES(?,?,?,?,?,?,?,?,?,?)",(ident,b.provider_id,b.asset.upper(),b.side,b.quantity,b.order_type,b.limit_price,"pending_review",time.time(),None))
 return {"id":ident,"status":"pending_review","message":"Proposta registrada. Nenhuma ordem enviada à corretora."}
@router.get("/finance/order-proposals")
def order_list():
 with db() as c:return [dict(x) for x in c.execute("SELECT * FROM order_proposals ORDER BY created DESC")]
@router.post("/finance/order-proposals/{oid}/approve")
def order_approve(oid:str):
 with db() as c:
  cur=c.execute("UPDATE order_proposals SET status='approved_not_executed',decision_at=? WHERE id=? AND status='pending_review'",(time.time(),oid))
  if not cur.rowcount:raise HTTPException(404,"Proposta pendente não encontrada.")
 return {"id":oid,"status":"approved_not_executed","message":"Aprovada, mas não executada. Exige adaptador oficial e confirmação final."}
@router.post("/finance/order-proposals/{oid}/execute")
def order_execute(oid:str):
 raise HTTPException(501,"Execução real desabilitada até implementar adaptador oficial da corretora, limites, idempotência e confirmação final.")

class IntelCaseIn(BaseModel):
 query:str=Field(min_length=2,max_length=200); purpose:str=Field(min_length=5,max_length=500)
@router.post("/intel/cases")
def intel_create(b:IntelCaseIn):
 ident=str(uuid.uuid4())
 with db() as c:c.execute("INSERT INTO intel_cases VALUES(?,?,?,?,?)",(ident,b.query,b.purpose,"open",time.time()))
 return {"id":ident,"status":"open","message":"Caso criado; use fontes públicas ou APIs oficiais autorizadas."}
@router.get("/intel/cases")
def intel_list():
 with db() as c:return [dict(x) for x in c.execute("SELECT * FROM intel_cases ORDER BY created DESC")]
class EvidenceIn(BaseModel):
 url:str;title:str=Field(default="",max_length=300);snippet:str=Field(default="",max_length=3000);observed_at:str=Field(default="",max_length=80);source_type:str=Field(default="public_web",pattern="^(public_web|official_api|user_supplied)$")
@router.post("/intel/cases/{cid}/evidence")
def intel_evidence_add(cid:str,b:EvidenceIn):
 p=urlparse(b.url)
 if p.scheme!="https" or not p.hostname:raise HTTPException(400,"Evidência exige URL HTTPS.")
 with db() as c:
  if not c.execute("SELECT 1 FROM intel_cases WHERE id=?",(cid,)).fetchone():raise HTTPException(404,"Caso não encontrado.")
  ident=str(uuid.uuid4());c.execute("INSERT INTO intel_evidence VALUES(?,?,?,?,?,?,?,?)",(ident,cid,b.url,b.title,b.snippet,b.observed_at,b.source_type,time.time()))
 return {"id":ident,"case_id":cid}
@router.get("/intel/cases/{cid}/evidence")
def intel_evidence_list(cid:str):
 with db() as c:return [dict(x) for x in c.execute("SELECT * FROM intel_evidence WHERE case_id=? ORDER BY created DESC",(cid,))]
