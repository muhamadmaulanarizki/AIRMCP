"""Production security policy shared by the MCP server and dashboard."""
import os
import ipaddress
import socket
from urllib.parse import urlparse


ROOT = os.path.dirname(os.path.abspath(__file__))
DANGEROUS_TOOLS = {
    "exec_cmd", "web_fetch", "artisan", "composer", "mysql_query",
    "scaffold_crud", "project_create", "project_register",
    "provider_create", "provider_delete",
}
SENSITIVE_NAMES = {
    ".env", "providers.json", "id_rsa", "id_ed25519",
}


def env_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def production_mode():
    return env_flag("AIRMCP_PRODUCTION")


def dashboard_token():
    return os.environ.get("AIRMCP_DASHBOARD_TOKEN", "").strip()


def allowed_dangerous_tools():
    raw = os.environ.get("AIRMCP_ALLOWED_DANGEROUS_TOOLS", "")
    return {item.strip() for item in raw.split(",") if item.strip()}


def tool_allowed(name):
    if not production_mode() or name not in DANGEROUS_TOOLS:
        return True
    allowed = allowed_dangerous_tools()
    return "*" in allowed or name in allowed


def ensure_tool_allowed(name):
    if not tool_allowed(name):
        raise PermissionError(
            f"Tool '{name}' dinonaktifkan dalam mode production. "
            "Tambahkan namanya ke AIRMCP_ALLOWED_DANGEROUS_TOOLS jika memang diperlukan."
        )


def _configured_roots():
    roots = []
    raw = os.environ.get("AIRMCP_ALLOWED_ROOTS", "")
    if raw:
        roots.extend(part.strip() for part in raw.split(os.pathsep) if part.strip())
    try:
        import projects
        roots.extend(item.get("path") for item in projects.list_projects() if item.get("exists"))
    except Exception:  # pragma: no cover - registry failure is handled as no roots
        pass
    return tuple(dict.fromkeys(os.path.realpath(os.path.abspath(root)) for root in roots if root))


def allowed_roots():
    return _configured_roots()


def _is_sensitive(path):
    name = os.path.basename(path).lower()
    return (
        name in SENSITIVE_NAMES
        or name.startswith(".env.")
        or name.endswith((".pem", ".key", ".p12", ".pfx"))
    )


def ensure_allowed_path(path, *, allow_missing=False):
    """Return a canonical path, enforcing registered/configured roots in production."""
    if path is None or not str(path).strip():
        raise ValueError("path wajib diisi")
    resolved = os.path.realpath(os.path.abspath(os.path.expanduser(str(path))))
    if not production_mode():
        return resolved
    if _is_sensitive(resolved):
        raise PermissionError("Akses file sensitif ditolak dalam mode production")
    roots = _configured_roots()
    allowed = False
    for root in roots:
        try:
            if os.path.commonpath((resolved, root)) == root:
                allowed = True
                break
        except ValueError:  # different drives on Windows
            continue
    if not allowed:
        raise PermissionError(
            "Path berada di luar project terdaftar/AIRMCP_ALLOWED_ROOTS: " + resolved
        )
    if not allow_missing and not os.path.exists(resolved):
        raise FileNotFoundError(resolved)
    return resolved


def ensure_safe_url(url):
    """Reject non-HTTP and private-network fetches in production."""
    parsed = urlparse(str(url))
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL harus menggunakan http/https dan memiliki host")
    if parsed.username or parsed.password:
        raise ValueError("Credential di dalam URL tidak diizinkan")
    if not production_mode() or env_flag("AIRMCP_ALLOW_PRIVATE_NETWORK"):
        return str(url)
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443)}
    except socket.gaierror as exc:
        raise ValueError("Host tidak dapat di-resolve") from exc
    for value in addresses:
        address = ipaddress.ip_address(value)
        if not address.is_global:
            raise PermissionError("Akses web ke jaringan private/local ditolak")
    return str(url)
