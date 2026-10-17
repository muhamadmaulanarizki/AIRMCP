"""AirMCP Dashboard - web UI untuk MCP server.

Serves ui/dashboard.html and exposes JSON API endpoints that proxy
to the MCP server via STDIO (JSON-RPC 2.0).

Start: python dashboard.py  ->  http://localhost:8765
No external dependencies (stdlib only).
"""
import json
import base64
import collections
import hmac
import os
import queue
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

import security as security_policy

ROOT = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(ROOT, "ui", "dashboard.html")
RUN_STATE_PATH = os.path.join(ROOT, "ui", "run_state.js")
PORT = 8765

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class StdioClient:
    """Thread-safe single-connection MCP client over STDIO."""

    def __init__(self):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        self.lock = threading.Lock()
        self._id = 0
        py = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
        if not os.path.exists(py):
            py = sys.executable
        self.proc = subprocess.Popen(
            [py, os.path.join(ROOT, "mcp_server.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", cwd=ROOT, env=env,
        )
        self.messages = queue.Queue()
        threading.Thread(target=self._read_stdout, daemon=True).start()
        initialized = self.rpc("initialize", {
            "protocolVersion": "2026-07-28", "capabilities": {},
            "clientInfo": {"name": "dashboard", "version": "1.0"},
        })
        if "error" in initialized:
            self.close()
            raise RuntimeError(initialized["error"]["message"])
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        self.proc.stdin.flush()

    def _read_stdout(self):
        try:
            for line in self.proc.stdout:
                self.messages.put(json.loads(line))
        finally:
            self.proc.stdout.close()
            self.messages.put(None)

    def rpc(self, method, params=None):
        with self.lock:
            self._id += 1
            req = {"jsonrpc": "2.0", "id": self._id, "method": method}
            if params is not None:
                req["params"] = params
            self.proc.stdin.write(json.dumps(req) + "\n")
            self.proc.stdin.flush()
            deadline = time.monotonic() + 300
            while True:
                try:
                    msg = self.messages.get(timeout=max(0, deadline - time.monotonic()))
                except queue.Empty:
                    self.close()
                    raise TimeoutError("MCP request timed out after 300 seconds")
                if msg is None:
                    return {"error": {"code": -32603, "message": "Server closed"}}
                if msg.get("id") == self._id and ("error" in msg or "result" in msg):
                    return msg

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()
            self.proc.wait(timeout=5)


class ClientPool:
    """Small pool of MCP stdio clients so slow calls don't block fast ones."""

    def __init__(self, size=5):
        self.size = max(1, size)
        self.free = []
        self.made = 0
        self.lock = threading.Lock()

    def acquire(self):
        with self.lock:
            if self.free:
                return self.free.pop()
            if self.made < self.size:
                self.made += 1
                make = True
            else:
                make = False
        if not make:
            return self._wait()
        try:
            return StdioClient()
        except Exception:
            with self.lock:
                self.made -= 1
            raise

    def _wait(self):
        for _ in range(600):
            time.sleep(0.02)
            with self.lock:
                if self.free:
                    return self.free.pop()
        raise TimeoutError("MCP is busy; please retry shortly")

    def release(self, c):
        with self.lock:
            if c.proc.poll() is None and len(self.free) < self.size:
                self.free.append(c)
                return
            self.made -= 1
        c.close()

    def rpc(self, method, params=None):
        c = self.acquire()
        try:
            return c.rpc(method, params)
        finally:
            self.release(c)

    def close_all(self):
        with self.lock:
            clients, self.free = self.free, []
        for c in clients:
            c.close()


pool = None


def rpc(method, params=None):
    return pool.rpc(method, params)


class RequestLimiter:
    """Small in-memory per-IP limiter for production dashboard APIs."""

    def __init__(self):
        self.lock = threading.Lock()
        self.hits = {}

    def allow(self, address):
        if not security_policy.production_mode():
            return True
        limit = max(1, int(os.environ.get("AIRMCP_RATE_LIMIT_PER_MINUTE", "240")))
        now = time.monotonic()
        with self.lock:
            bucket = self.hits.setdefault(address, collections.deque())
            while bucket and bucket[0] <= now - 60:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True

    def clear(self):
        with self.lock:
            self.hits.clear()


rate_limiter = RequestLimiter()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "AirMCP"
    sys_version = ""

    def log_message(self, fmt, *args):  # quieter
        pass

    def _emit(self, obj):
        """Write one NDJSON line to the client (streaming endpoints)."""
        try:
            self.wfile.write((json.dumps(obj, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    # ---------- helpers ----------
    def _security_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")

    def _authorized(self):
        token = security_policy.dashboard_token()
        if not token and not security_policy.production_mode():
            return True
        supplied = self.headers.get("X-AirMCP-Token", "")
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            supplied = auth[7:].strip()
        elif auth.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth[6:].strip(), validate=True).decode("utf-8")
                supplied = decoded.partition(":")[2]
            except (ValueError, UnicodeDecodeError):
                supplied = ""
        return bool(token) and hmac.compare_digest(supplied, token)

    def _send_unauthorized(self):
        body = b'{"error":"authentication required"}'
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="AirMCP", charset="UTF-8"')
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._security_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_rate_limited(self):
        body = b'{"error":"rate limit exceeded"}'
        self.send_response(429)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Retry-After", "60")
        self._security_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _rate_allowed(self):
        path = urlparse(self.path).path
        return not path.startswith("/api/") or rate_limiter.allow(self.client_address[0])

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
        except ValueError:
            self.close_connection = True
            return None
        if length < 0 or length > 2_000_000:
            self.close_connection = True
            return None
        if not length:
            return {}
        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
            return value if isinstance(value, dict) else None
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    # ---------- routes ----------
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/healthz":
            self._send_json({"status": "ok"})
            return
        if path == "/readyz":
            try:
                response = rpc("ping")
                ready = "error" not in response
                self._send_json({"status": "ready" if ready else "not-ready"}, 200 if ready else 503)
            except Exception:
                self._send_json({"status": "not-ready"}, 503)
            return
        if not self._authorized():
            self._send_unauthorized()
            return
        if not self._rate_allowed():
            self._send_rate_limited()
            return
        try:
            self._get()
        except Exception as exc:
            self._send_json({"error": str(exc)}, 503)

    def _get(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._serve_html()
        elif path == "/assets/run_state.js":
            self._serve_file(RUN_STATE_PATH, "text/javascript; charset=utf-8")
        elif path == "/api/server":
            resp = rpc("initialize", {"clientInfo": {"name": "dashboard", "version": "1.0"}})
            self._send_json(resp.get("result", resp.get("error", {})))
        elif path == "/api/tools":
            resp = rpc("tools/list")
            self._send_json(resp.get("result", resp.get("error", {})))
        elif path == "/api/resources":
            resp = rpc("resources/list")
            self._send_json(resp.get("result", resp.get("error", {})))
        elif path == "/api/prompts":
            resp = rpc("prompts/list")
            self._send_json(resp.get("result", resp.get("error", {})))
        elif path == "/api/agents":
            resp = rpc("tools/call", {"name": "agent_list", "arguments": {}})
            self._send_json(_data(resp))
        elif path == "/api/projects":
            resp = rpc("tools/call", {"name": "project_list", "arguments": {}})
            self._send_json(_data(resp))
        elif path == "/api/providers":
            resp = rpc("tools/call", {"name": "provider_list", "arguments": {}})
            self._send_json(_data(resp))
        elif path == "/api/fs":
            params = parse_qs(urlparse(self.path).query)
            self._send_json(list_fs(params.get("path", [""])[0]))
        elif path == "/api/route":
            params = parse_qs(urlparse(self.path).query)
            msg = params.get("message", [""])[0]
            resp = rpc("tools/call", {"name": "route_agent", "arguments": {"message": msg}})
            self._send_json(_data(resp))
        elif path == "/api/plan":
            params = parse_qs(urlparse(self.path).query)
            task = params.get("message", [""])[0]
            resp = rpc("tools/call", {"name": "plan_task", "arguments": {"task": task}})
            self._send_json(_data(resp))
        elif path == "/api/docs":
            params = parse_qs(urlparse(self.path).query)
            resp = rpc("tools/call", {"name": "doc_list", "arguments": {"project": params.get("project", [""])[0]}})
            self._send_json(_data(resp))
        elif path == "/api/doc":
            params = parse_qs(urlparse(self.path).query)
            resp = rpc("tools/call", {"name": "doc_read", "arguments": {
                "project": params.get("project", [""])[0], "type": params.get("type", ["PRD"])[0]}})
            self._send_json(_data(resp))
        elif path == "/api/docs/questions":
            params = parse_qs(urlparse(self.path).query)
            resp = rpc("tools/call", {"name": "doc_questions",
                                      "arguments": {"type": params.get("type", ["PRD"])[0]}})
            self._send_json(_data(resp))
        elif path == "/api/notes":
            params = parse_qs(urlparse(self.path).query)
            resp = rpc("tools/call", {"name": "note_list", "arguments": {"project": params.get("project", [""])[0]}})
            self._send_json(_data(resp))
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        if not self._authorized():
            self._send_unauthorized()
            return
        if not self._rate_allowed():
            self._send_rate_limited()
            return
        path = urlparse(self.path).path
        body = self._read_body()
        if body is None:
            self._send_json({"error": "invalid JSON body"}, 400)
            return
        try:
            if path == "/api/tools/call":
                resp = rpc("tools/call", {
                    "name": body.get("name"),
                    "arguments": body.get("arguments") or {},
                })
                self._send_json(_unwrap(resp))
            elif path == "/api/resources/read":
                resp = rpc("resources/read", {"uri": body.get("uri", "")})
                self._send_json(resp.get("result", resp.get("error", {})))
            elif path == "/api/prompts/get":
                resp = rpc("prompts/get", {
                    "name": body.get("name"),
                    "arguments": body.get("arguments") or {},
                })
                self._send_json(resp.get("result", resp.get("error", {})))
            elif path == "/api/elicitation":
                resp = rpc("elicitation/create", body or {})
                self._send_json(resp.get("result", resp.get("error", {})))
            elif path == "/api/orchestrate":
                resp = rpc("tools/call", {"name": "orchestrate", "arguments": body or {}})
                self._send_json(_unwrap(resp))
            elif path == "/api/agents/run":
                resp = rpc("tools/call", {"name": "agent_run", "arguments": body or {}})
                self._send_json(_unwrap(resp))
            elif path == "/api/agents/create":
                resp = rpc("tools/call", {"name": "agent_create", "arguments": body or {}})
                self._send_json(_unwrap(resp))
            elif path == "/api/projects/resolve":
                resp = rpc("tools/call", {"name": "project_resolve", "arguments": body or {}})
                self._send_json(_unwrap(resp))
            elif path == "/api/projects/create":
                resp = rpc("tools/call", {"name": "project_create", "arguments": body or {}})
                self._send_json(_unwrap(resp))
            elif path == "/api/projects/select":
                resp = rpc("tools/call", {"name": "project_select", "arguments": body or {}})
                self._send_json(_unwrap(resp))
            elif path == "/api/agents/delete":
                resp = rpc("tools/call", {"name": "agent_delete", "arguments": body or {}})
                self._send_json(_unwrap(resp))
            elif path == "/api/providers/create":
                resp = rpc("tools/call", {"name": "provider_create", "arguments": body or {}})
                self._send_json(_unwrap(resp))
            elif path == "/api/providers/delete":
                resp = rpc("tools/call", {"name": "provider_delete", "arguments": body or {}})
                self._send_json(_unwrap(resp))
            elif path == "/api/chat":
                resp = rpc("tools/call", {"name": "llm_chat", "arguments": body or {}})
                self._send_json(_unwrap(resp))
            elif path == "/api/doc":
                resp = rpc("tools/call", {"name": "doc_generate", "arguments": body or {}})
                self._send_json(_unwrap(resp))
            elif path == "/api/notes":
                resp = rpc("tools/call", {"name": "note_add", "arguments": body or {}})
                self._send_json(_unwrap(resp))
            elif path == "/api/notes/update":
                resp = rpc("tools/call", {"name": "note_update", "arguments": body or {}})
                self._send_json(_unwrap(resp))
            elif path == "/api/notes/delete":
                resp = rpc("tools/call", {"name": "note_delete", "arguments": body or {}})
                self._send_json(_unwrap(resp))
            elif path == "/api/docs/delete":
                resp = rpc("tools/call", {"name": "doc_delete", "arguments": body or {}})
                self._send_json(_unwrap(resp))
            elif path == "/api/docs/build":
                resp = rpc("tools/call", {"name": "doc_build", "arguments": body or {}})
                self._send_json(_unwrap(resp))
            elif path == "/api/orchestrate/stream":
                self._stream_orchestrate(body or {})
            else:
                self._send_json({"error": "not found"}, 404)
        except Exception as e:  # noqa: BLE001
            self._send_json({"error": f"{type(e).__name__}: {e}"}, 500)

    def _stream_orchestrate(self, body):
        """Server-streaming orchestrate: emit NDJSON per turn (real-time)."""
        import orchestrator as orch
        from mcp_server import _local_tool_executor, _tools_spec
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self._security_headers()
        self.end_headers()
        self.close_connection = True
        if body.get("simulate"):
            sim = True
        else:
            sim = None if orch.available_providers() else True
        try:
            res = orch.orchestrate(
                body.get("task"), project=body.get("project"), path=body.get("path"),
                team=body.get("team"), mode=body.get("mode", "pipeline"),
                rounds=body.get("rounds", 2), tool_executor=_local_tool_executor, tools_spec=_tools_spec(),
                allow_simulation=sim,
                on_status=lambda e: self._emit({"type": "status", **e}),
                on_turn=lambda e: self._emit({"type": "turn", **e}))
            self._emit({"type": "done", "simulated": res.get("simulated"),
                        "project": res.get("project"), "path": res.get("path"),
                        "providers": res.get("providers_available"),
                        "count": len(res.get("transcript", []))})
        except Exception as e:  # noqa: BLE001
            self._emit({"type": "error", "message": f"{type(e).__name__}: {e}"})

    def _serve_html(self):
        try:
            with open(HTML_PATH, "r", encoding="utf-8") as f:
                body = f.read().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self._security_headers()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self._send_json({"error": "ui/dashboard.html not found"}, 500)

    def _serve_file(self, path, content_type):
        try:
            with open(path, "rb") as file:
                body = file.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self._security_headers()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self._send_json({"error": "asset not found"}, 404)


def _unwrap(resp):
    """Flatten MCP tools/call response for the UI."""
    if "error" in resp:
        return resp["error"]
    r = resp.get("result", {})
    return {
        "isError": bool(r.get("isError")),
        "structuredContent": r.get("structuredContent"),
        "text": "\n".join(c["text"] for c in r.get("content", []) if c.get("type") == "text"),
    }


def _data(resp):
    result = _unwrap(resp)
    if result.get("isError") or "code" in result:
        return result
    return result.get("structuredContent") or {}


def list_fs(path):
    """Directory listing for the dashboard folder browser."""
    import string
    path = (path or "").strip()
    if not path:
        if security_policy.production_mode():
            roots = list(security_policy.allowed_roots())
            return {"path": "", "parent": None, "isRoot": True, "dirs": roots, "files": []}
        drives = [d + ":\\" for d in string.ascii_uppercase if os.path.exists(d + ":\\")]
        return {"path": "", "parent": None, "isRoot": True, "dirs": drives, "files": []}
    path = security_policy.ensure_allowed_path(path)
    if not os.path.isdir(path):
        nxt = os.path.dirname(path)
        path = nxt if os.path.isdir(nxt) else os.path.splitdrive(path)[0] + os.sep
    try:
        items = os.listdir(path)
    except OSError as e:
        return {"error": str(e), "path": path, "dirs": [], "files": []}
    dirs, files = [], []
    for name in items:
        full = os.path.join(path, name)
        try:
            (dirs if os.path.isdir(full) else files).append(name)
        except OSError:
            pass
    dirs.sort(key=str.lower)
    files.sort(key=str.lower)
    parent = os.path.dirname(path.rstrip("\\/"))
    if security_policy.production_mode():
        try:
            parent = security_policy.ensure_allowed_path(parent)
        except (PermissionError, FileNotFoundError, ValueError):
            parent = ""
    is_root = not parent or os.path.normcase(parent) == os.path.normcase(path)
    return {"path": path, "parent": (None if is_root else parent), "isRoot": is_root,
            "dirs": dirs[:400], "files": files[:400]}


class QuietServer(ThreadingHTTPServer):
    # On Windows allow_reuse_address would co-bind onto an already-listening
    # socket and steal nothing — force a clean bind or pick another port.
    allow_reuse_address = False

    def handle_error(self, request, client_address):
        """Jangan berisik untuk koneksi yang ditutup klien (keep-alive/browser)."""
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


def free_port(start, tries=8, host="127.0.0.1"):
    for p in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, p))
                return p
            except OSError:
                continue
    raise RuntimeError(f"No free port in {start}..{start + tries - 1}")


def main():
    global pool, PORT
    host = os.environ.get("AIRMCP_HOST", "127.0.0.1").strip() or "127.0.0.1"
    token = security_policy.dashboard_token()
    if security_policy.production_mode() and not token:
        raise RuntimeError("AIRMCP_DASHBOARD_TOKEN wajib diisi dalam mode production")
    if host not in {"127.0.0.1", "localhost", "::1"} and not token:
        raise RuntimeError("Bind non-local membutuhkan AIRMCP_DASHBOARD_TOKEN")
    pool = ClientPool()
    start_port = int(os.environ.get("AIRMCP_PORT", "8765"))
    PORT = free_port(start_port, host=host)
    browser_host = "localhost" if host in {"0.0.0.0", "::"} else host
    url = f"http://{browser_host}:{PORT}"
    print(f"[dashboard] MCP server ready")
    print(f"[dashboard] open {url}")

    def open_browser():
        try:
            webbrowser.open(url)
        except Exception as e:  # noqa: BLE001
            print(f"[dashboard] browser not opened: {e}")

    if not security_policy.production_mode() and not security_policy.env_flag("AIRMCP_NO_BROWSER"):
        t = threading.Timer(0.6, open_browser)
        t.daemon = True
        t.start()
    srv = QuietServer((host, PORT), Handler)
    print(f"[dashboard] listening on {host}:{PORT}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        pool.close_all()
        print("[dashboard] stopped", flush=True)


if __name__ == "__main__":
    main()
