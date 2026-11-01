"""Local-only access boundary, security headers and persistent local secret key."""
import ipaddress
import os
from pathlib import Path

from cryptography.fernet import Fernet
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


def _read_key_from_env_file():
    """Read an existing local .env key when the CLI did not export it."""
    candidates = (Path(__file__).resolve().parent / ".env", Path.cwd() / ".env")
    for env_file in candidates:
        try:
            lines = env_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            key, separator, value = line.partition("=")
            if separator and key.strip() == "KAMY_MASTER_KEY":
                value = value.strip().strip("\"'").strip()
                if value:
                    return value
    return None


def ensure_local_master_key(data_dir=None):
    """Load or create one stable Fernet key in the local data directory.

    An explicit KAMY_MASTER_KEY always wins. When it is absent, an existing
    .env value is preferred; otherwise data/.master_key is created atomically
    with owner-only permissions. The key is never regenerated over an existing
    file, which prevents saved credentials from becoming unreadable.
    """
    key = os.getenv("KAMY_MASTER_KEY", "").strip()
    if key:
        return key

    key = _read_key_from_env_file()
    if key:
        os.environ["KAMY_MASTER_KEY"] = key
        return key

    directory = Path(data_dir or os.getenv("KAMY_DATA_DIR", "./data")).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    key_path = directory / ".master_key"

    try:
        key = key_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        generated = Fernet.generate_key().decode("ascii")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        try:
            descriptor = os.open(str(key_path), flags, 0o600)
        except FileExistsError:
            key = key_path.read_text(encoding="utf-8").strip()
        else:
            try:
                os.write(descriptor, (generated + "\n").encode("ascii"))
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            key = generated
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass

    try:
        Fernet(key.encode("ascii"))
    except Exception as error:
        raise RuntimeError(
            "A chave mestra local em data/.master_key é inválida. "
            "Não a substitua: restaure a chave original ou o backup."
        ) from error

    os.environ["KAMY_MASTER_KEY"] = key
    return key


# Test fixtures deliberately control the key themselves. Normal desktop and
# Docker launches get a stable key before FastAPI initializes its database.
if os.getenv("KAMY_TESTING") != "1":
    ensure_local_master_key()


class LocalOnlyMiddleware(BaseHTTPMiddleware):
    """Only accept requests originating from loopback interfaces."""
    async def dispatch(self, request, call_next):
        host = request.client.host if request.client else ""
        if os.getenv("KAMY_TESTING") == "1" and host == "testclient":
            return await call_next(request)
        try:
            address = ipaddress.ip_address(host)
            is_local = address.is_loopback
            # Compose publishes the host port on 127.0.0.1 only; Docker reaches
            # the container through its private bridge address.
            if not is_local and os.getenv("KAMY_DOCKER_LOCAL") == "1":
                is_local = address.is_private
        except ValueError:
            is_local = False
        if not is_local:
            return JSONResponse(
                {"detail": "Kamy Bot is local-only. Connect through localhost."},
                status_code=403,
            )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; connect-src 'self'; base-uri 'self'; "
            "frame-ancestors 'none'",
        )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response
