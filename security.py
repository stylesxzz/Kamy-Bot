"""Production-oriented single-admin session and CSRF protection for Kamy Bot."""
import base64, hashlib, hmac, json, os, secrets, time
from collections import defaultdict, deque
from urllib.parse import urlparse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse

COOKIE="kamy_session"
CSRF_COOKIE="kamy_csrf"
WINDOW=300
MAX_FAILURES=8
_failures=defaultdict(deque)

def _secret():
    value=os.getenv("KAMY_SESSION_SECRET","")
    if len(value)<32:
        raise RuntimeError("KAMY_SESSION_SECRET must contain at least 32 random characters.")
    return value.encode()

def _admin_password():
    value=os.getenv("KAMY_ADMIN_PASSWORD","")
    if len(value)<16:
        raise RuntimeError("KAMY_ADMIN_PASSWORD must contain at least 16 characters.")
    return value

def _sign(payload):
    raw=base64.urlsafe_b64encode(json.dumps(payload,separators=(",",":")).encode()).decode().rstrip("=")
    sig=base64.urlsafe_b64encode(hmac.new(_secret(),raw.encode(),hashlib.sha256).digest()).decode().rstrip("=")
    return raw+"."+sig

def _read(token):
    try:
        raw,sig=token.split(".",1)
        expected=base64.urlsafe_b64encode(hmac.new(_secret(),raw.encode(),hashlib.sha256).digest()).decode().rstrip("=")
        if not hmac.compare_digest(sig,expected):return None
        data=json.loads(base64.urlsafe_b64decode(raw+"="*((4-len(raw)%4)%4)))
        if data.get("exp",0)<time.time():return None
        return data
    except Exception:return None

def _login_html():
    return """<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>Kamy Bot · Login</title><style>*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#10091a;color:#f5eafa;font:15px system-ui}.card{width:min(92vw,390px);padding:30px;border:1px solid #594064;border-radius:20px;background:#1c1128;box-shadow:0 20px 80px #0008}img{width:76px}h1{font-size:24px;margin:10px 0}p{color:#bcaac8;font-size:13px}label{display:block;margin:18px 0 7px;font-size:12px}input{width:100%;padding:13px;border-radius:9px;border:1px solid #594064;background:#10091a;color:white}button{width:100%;margin-top:18px;padding:13px;border:0;border-radius:9px;background:linear-gradient(100deg,#7750bc,#bd67ae);color:white;font-weight:700}#err{color:#ff9aaf;min-height:20px;font-size:12px}</style><main class="card"><img src="/assets/kamy-mascot.svg" alt="Kamy"><h1>Entrar no Kamy Bot</h1><p>Área privada do administrador. Entre com suas credenciais.</p><form id="f"><label>Usuário</label><input name="username" autocomplete="username" required><label>Senha</label><input name="password" type="password" autocomplete="current-password" required><button>Entrar</button><div id="err"></div></form></main><script>document.querySelector("#f").onsubmit=async e=>{e.preventDefault();let d=Object.fromEntries(new FormData(e.target));let r=await fetch("/api/auth/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(d)});let j=await r.json();if(r.ok)location.href="/";else document.querySelector("#err").textContent=j.detail||"Falha no login"}</script></html>"""

class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self,request,call_next):
        path=request.url.path
        if path in ("/api/health","/login","/api/auth/login") or path.startswith("/static/") or path.startswith("/assets/"):
            return await call_next(request)
        if path=="/api/extensions/oauth/callback" and request.method=="GET":
            return await call_next(request)
        # The production app is fail-closed: missing admin credentials never grants anonymous access.
        try:_secret();_admin_password()
        except RuntimeError as exc:
            return JSONResponse({"detail":str(exc),"setup_required":True},status_code=503)
        session=_read(request.cookies.get(COOKIE,""))
        if not session:
            if path=="/":return HTMLResponse(_login_html(),status_code=200)
            return JSONResponse({"detail":"Authentication required"},status_code=401)
        request.state.kamy_user=session["sub"]
        if request.method in ("POST","PUT","PATCH","DELETE"):
            origin=request.headers.get("origin")
            if origin:
                parsed=urlparse(origin)
                if parsed.netloc!=request.url.netloc:
                    return JSONResponse({"detail":"Cross-origin request blocked"},status_code=403)
            csrf=request.headers.get("x-csrf-token","")
            if not csrf or not hmac.compare_digest(csrf,session.get("csrf","")) or csrf!=request.cookies.get(CSRF_COOKIE,""):
                return JSONResponse({"detail":"CSRF validation failed"},status_code=403)
        response=await call_next(request)
        return response

def login(username,password,client_ip):
    now=time.time(); q=_failures[client_ip]
    while q and q[0]<now-WINDOW:q.popleft()
    if len(q)>=MAX_FAILURES: return None, "Too many login attempts. Try again in five minutes."
    expected_user=os.getenv("KAMY_ADMIN_USERNAME","admin")
    try: expected_password=_admin_password();_secret()
    except RuntimeError as exc:return None,str(exc)
    ok=hmac.compare_digest(username,expected_user) and hmac.compare_digest(password,expected_password)
    if not ok:
        q.append(now)
        return None,"Invalid username or password."
    q.clear()
    csrf=secrets.token_urlsafe(32)
    return {"token":_sign({"sub":username,"csrf":csrf,"exp":now+12*3600}),"csrf":csrf},None

def apply_session(response,session):
    secure=os.getenv("KAMY_COOKIE_SECURE","1").lower() in ("1","true","yes","on")
    response.set_cookie(COOKIE,session["token"],httponly=True,secure=secure,samesite="strict",max_age=43200,path="/")
    response.set_cookie(CSRF_COOKIE,session["csrf"],httponly=False,secure=secure,samesite="strict",max_age=43200,path="/")
    response.headers["Cache-Control"]="no-store"
    return response

def clear_session(response):
    secure=os.getenv("KAMY_COOKIE_SECURE","1").lower() in ("1","true","yes","on")
    response.delete_cookie(COOKIE,path="/",secure=secure,httponly=True,samesite="strict")
    response.delete_cookie(CSRF_COOKIE,path="/",secure=secure,samesite="strict")
    return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self,request,call_next):
        response=await call_next(request)
        response.headers.setdefault("X-Content-Type-Options","nosniff")
        response.headers.setdefault("X-Frame-Options","DENY")
        response.headers.setdefault("Referrer-Policy","strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy","camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Cross-Origin-Opener-Policy","same-origin")
        response.headers.setdefault("Content-Security-Policy","default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; base-uri 'self'; frame-ancestors 'none'")
        if request.url.scheme=="https" or request.headers.get("x-forwarded-proto","").split(",")[0].strip()=="https":
            response.headers.setdefault("Strict-Transport-Security","max-age=31536000; includeSubDomains")
        if request.url.path.startswith("/api/"):response.headers["Cache-Control"]="no-store"
        return response
