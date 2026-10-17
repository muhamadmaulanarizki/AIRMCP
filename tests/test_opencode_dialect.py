"""Replicate opencode v1.19.0 dialect end-to-end (2025-11-25, id:0 start).

Asserts: tools/list response must NOT contain `icons` for this dialect.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = str(Path(__file__).resolve().parents[1])
venv_python = Path(ROOT, ".venv", "Scripts", "python.exe")
PY = str(venv_python if venv_python.exists() else Path(sys.executable))

env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
proc = subprocess.Popen(
    [PY, os.path.join(ROOT, "mcp_server.py")],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    text=True, encoding="utf-8", cwd=ROOT, env=env, shell=False,
)


def send(msg):
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()


def recv():
    return json.loads(proc.stdout.readline())


# 1. initialize — exactly what opencode sent (from RAW trace)
send({"method": "initialize",
      "params": {"protocolVersion": "2025-11-25", "capabilities": {"roots": {}},
                 "clientInfo": {"name": "opencode", "version": "1.19.0"}},
      "jsonrpc": "2.0", "id": 0})
r = recv()
ok1 = r["result"]["protocolVersion"] == "2025-11-25" and set(r["result"]["capabilities"].keys()) <= \
    {"tools", "resources", "prompts"}
print(("PASS" if ok1 else "FAIL") + "  initialize echoes 2025-11-25, caps minimal")
print("    caps =", list(r["result"]["capabilities"].keys()))

# 2. notifications/initialized (no response expected)
send({"method": "notifications/initialized", "jsonrpc": "2.0"})

# 3. tools/list — MUST have no `icons` for 2025 dialect
send({"method": "tools/list", "jsonrpc": "2.0", "id": 1})
r = recv()
tools = r["result"]["tools"]
ok2 = all("icons" not in t for t in tools) and len(tools) >= 4
print(("PASS" if ok2 else "FAIL") + f"  tools/list x{len(tools)} sans `icons` (2025 dialect)")
print("    tools =", [t["name"] for t in tools])

# 4. prompts/list + resources/list also stripped
send({"method": "prompts/list", "jsonrpc": "2.0", "id": 2})
send({"method": "resources/list", "jsonrpc": "2.0", "id": 3})
r2, r3 = recv(), recv()
ok3 = all("icons" not in p for p in r2["result"]["prompts"]) and \
      all("icons" not in rr for rr in r3["result"]["resources"])
print(("PASS" if ok3 else "FAIL") + "  prompts/resources sans `icons`")

# 5. tools/call still works
send({"method": "tools/call", "params": {"name": "read_file", "arguments": {"path": os.path.join(ROOT, "requirements.txt")}}, "jsonrpc": "2.0", "id": 4})
r = recv()
ok4 = "content" in r.get("result", {})
print(("PASS" if ok4 else "FAIL") + "  tools/call works in-opencode-dialect")

proc.stdin.close()
try:
    proc.wait(timeout=5)
except Exception:
    proc.kill()

ok = ok1 and ok2 and ok3 and ok4
print("===", "OPECODE DIALECT: ALL PASS" if ok else "FAILED", "===")
sys.exit(0 if ok else 1)
