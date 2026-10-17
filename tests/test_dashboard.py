"""Smoke test dashboard.py over HTTP (spawns, probes, kills)."""
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8765

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def kill_stale_listeners(port):
    """Kill leftover processes listening on port (Windows: netstat + taskkill)."""
    try:
        out = subprocess.run(
            f"netstat -ano -p tcp", shell=True, capture_output=True, text=True, timeout=15
        ).stdout
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0] == "TCP" and parts[1].endswith(f":{port}") \
                    and parts[3] == "LISTENING":
                pid = parts[4]
                subprocess.run(["taskkill", "/F", "/PID", pid],
                               capture_output=True, text=True, timeout=10)
                print(f"  (killed stale listener PID {pid})")
    except Exception as e:  # noqa: BLE001
        print(f"  (stale check skipped: {e})")


def main():
    kill_stale_listeners(PORT)
    proc = subprocess.Popen(
        [sys.executable, "-u", os.path.join(ROOT, "dashboard.py")],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", cwd=ROOT, shell=False,
    )
    # read the actual bound port from dashboard stdout
    port_used = PORT
    try:
        for _ in range(80):
            line = proc.stdout.readline()
            if not line:
                break
            if "listening on" in line:
                port_used = int(line.strip().rsplit(":", 1)[1])
                break
    except Exception:
        pass
    base = f"http://127.0.0.1:{port_used}"

    def get(path):
        with urllib.request.urlopen(base + path, timeout=8) as r:
            return json.loads(r.read().decode())

    def post(path, body):
        req = urllib.request.Request(
            base + path, method="POST",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())

    results = []
    try:
        html = urllib.request.urlopen(base + "/", timeout=8).read().decode()
        results.append(("GET / serves HTML", "AIRMCP" in html))
        asset = urllib.request.urlopen(base + "/assets/run_state.js", timeout=8).read().decode()
        results.append(("GET /assets/run_state.js", "class OrchestrationRun" in asset))
        results.append(("GET /healthz", get("/healthz").get("status") == "ok"))
        results.append(("GET /readyz", get("/readyz").get("status") == "ready"))

        server = get("/api/server")
        results.append(("GET /api/server", server.get("protocolVersion") == "2026-07-28"))

        tools = get("/api/tools")
        names = [t["name"] for t in tools.get("tools", [])]
        results.append(("GET /api/tools",
                        set(names) >= {"list_files", "read_file", "exec_cmd", "web_fetch"}))

        call = post("/api/tools/call",
                    {"name": "exec_cmd", "arguments": {"command": "echo dash-ok"}})
        results.append(("POST /api/tools/call",
                        call.get("structuredContent", {}).get("output") == "dash-ok"))

        err_call = post("/api/tools/call", {"name": "read_file", "arguments": {}})
        results.append(("POST tools/call error passthrough", err_call.get("code") == -32602))

        read = post("/api/resources/read", {"uri": "airmcp://info"})
        text = (read.get("contents") or [{}])[0].get("text") or ""
        results.append(("POST /api/resources/read", "airmcp-solo" in text))

        prompts = get("/api/prompts")
        results.append(("GET /api/prompts", len(prompts.get("prompts", [])) >= 3))

        pget = post("/api/prompts/get",
                    {"name": "code-review", "arguments": {"code": "x=1"}})
        results.append(("POST /api/prompts/get",
                        "Review the following code" in json.dumps(pget)))

        ppget = post("/api/prompts/get",
                     {"name": "demo-erp/analisa-po", "arguments": {"path": "po.csv"}})
        results.append(("POST /api/prompts/get project", "po.csv" in json.dumps(ppget)))

        agents = get("/api/agents")
        an = [a["name"] for a in agents.get("agents", [])]
        results.append(("GET /api/agents", {"architect", "coder"} <= set(an)))

        provs = get("/api/providers")
        pn = [p["name"] for p in provs.get("providers", [])]
        results.append(("GET /api/providers", {"openai", "deepseek", "hermes"} <= set(pn)))

        projs = get("/api/projects")
        jn = [p["project"] for p in projs.get("projects", [])]
        results.append(("GET /api/projects", "demo-erp" in jn))

        res = post("/api/projects/resolve", {"hint": "demo erp"})
        results.append(("POST /api/projects/resolve",
                        res.get("structuredContent", {}).get("resolved") is True))

        orch = post("/api/orchestrate",
                    {"task": "test fitur", "project": "demo-erp",
                     "team": "architect,coder", "mode": "pipeline", "simulate": True})
        oc = orch.get("structuredContent", {})
        results.append(("POST /api/orchestrate",
                        len(oc.get("transcript", [])) == 2 and oc.get("simulated") is True))

        ac = post("/api/agents/create", {"name": "dash-tmp", "title": "Dash Tmp", "provider": "auto"})
        results.append(("POST /api/agents/create",
                        ac.get("structuredContent", {}).get("saved") is True))
        ad = post("/api/agents/delete", {"name": "dash-tmp"})
        results.append(("POST /api/agents/delete",
                        ad.get("structuredContent", {}).get("deleted") is True))

        el = post("/api/elicitation", {"question": "Proceed?", "choices": ["yes", "no"]})
        results.append(("POST /api/elicitation", bool(el.get("elicitId"))))

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()

    passed = 0
    for name, ok in results:
        print(("PASS " if ok else "FAIL ") + name)
        passed += bool(ok)
    print(f"=== {passed}/{len(results)} passed ===")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
