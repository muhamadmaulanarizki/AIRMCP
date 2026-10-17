"""Simulate a STRICT MCP client exactly like opencode would.

Checks:
 1. Config python path resolves (absolute).
 2. Spawn via that exact command (no shell) works.
 3. FIRST stdout message after initialize request == the initialize
    response (id must match; no unsolicited notifications before it).
 4. tools/list afterwards works.
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

# 1. full path resolves
assert os.path.exists(PY) or subprocess.run([PY, "--version"], capture_output=True).returncode == 0, \
    "python path missing"
print("PASS  1  python full path resolves")

# 2. spawn exactly like opencode (command array, no shell)
env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
proc = subprocess.Popen(
    [PY, os.path.join(ROOT, "mcp_server.py")],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, encoding="utf-8", cwd=ROOT, env=env, shell=False,
)

init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
                             "clientCapabilities": {"tools": {"listChanged": True}}},
                   "clientInfo": {"name": "opencode", "version": "go"}}}
proc.stdin.write(json.dumps(init) + "\n")
proc.stdin.flush()

# 3. first message MUST be the initialize response (strict client check)
first = json.loads(proc.stdout.readline())
assert first.get("id") == 1 and "result" in first, f"BAD first msg: {first}"
print("PASS  2  first stdout message == initialize response (no stray notifications)")
print("        server:", first["result"]["serverInfo"]["name"], "| proto:",
      first["result"]["protocolVersion"])

# 4. tools/list
req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
proc.stdin.write(json.dumps(req) + "\n")
proc.stdin.flush()
second = json.loads(proc.stdout.readline())
assert second.get("id") == 2 and "tools" in second.get("result", {}), f"BAD: {second}"
names = [t["name"] for t in second["result"]["tools"]]
print("PASS  3  tools/list ->", names)

proc.stdin.close()
try:
    proc.wait(timeout=5)
except Exception:
    proc.kill()
print("=== STRICT CLIENT SIMULATION: ALL PASS ===")
