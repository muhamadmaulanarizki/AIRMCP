"""Production-mode integration test for auth, policy, sandbox, and health probes."""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = "integration-production-token"


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    missing_env = dict(os.environ)
    missing_env.update({"AIRMCP_PRODUCTION": "1", "AIRMCP_DASHBOARD_TOKEN": "", "AIRMCP_NO_BROWSER": "1"})
    rejected = subprocess.run(
        [sys.executable, "-u", os.path.join(ROOT, "dashboard.py")], cwd=ROOT,
        env=missing_env, capture_output=True, text=True, timeout=10,
    )
    assert rejected.returncode != 0
    assert "AIRMCP_DASHBOARD_TOKEN wajib" in (rejected.stdout + rejected.stderr)

    port = free_port()
    env = dict(os.environ)
    env.update({
        "AIRMCP_PRODUCTION": "1",
        "AIRMCP_DASHBOARD_TOKEN": TOKEN,
        "AIRMCP_HOST": "127.0.0.1",
        "AIRMCP_PORT": str(port),
        "AIRMCP_NO_BROWSER": "1",
        "AIRMCP_ALLOWED_DANGEROUS_TOOLS": "",
        "AIRMCP_ALLOWED_ROOTS": os.path.join(ROOT, "demo-erp"),
    })
    proc = subprocess.Popen(
        [sys.executable, "-u", os.path.join(ROOT, "dashboard.py")],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8",
    )
    base = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(base + "/healthz", timeout=1) as response:
                    if json.loads(response.read())["status"] == "ok":
                        break
            except Exception:
                time.sleep(0.1)
        else:
            raise RuntimeError("production dashboard did not become healthy")

        try:
            urllib.request.urlopen(base + "/", timeout=5)
            raise AssertionError("dashboard accepted an unauthenticated request")
        except urllib.error.HTTPError as exc:
            assert exc.code == 401

        def get(path):
            request = urllib.request.Request(base + path, headers={"X-AirMCP-Token": TOKEN})
            with urllib.request.urlopen(request, timeout=10) as response:
                return response, json.loads(response.read())

        response, ready = get("/readyz")
        assert ready["status"] == "ready"
        response, tools = get("/api/tools")
        names = {tool["name"] for tool in tools["tools"]}
        assert "exec_cmd" not in names and "read_file" in names
        assert response.headers["X-Frame-Options"] == "DENY"

        project = urllib.parse.quote(os.path.join(ROOT, "demo-erp"))
        _, listing = get("/api/fs?path=" + project)
        assert "dirs" in listing

        outside = urllib.parse.quote(ROOT)
        try:
            get("/api/fs?path=" + outside)
            raise AssertionError("filesystem browser escaped the sandbox")
        except urllib.error.HTTPError as exc:
            assert exc.code == 503

        print("PASS: production auth, headers, health, tool policy, and path sandbox")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
