"""Replicate opencode-go's actual behavior: initialize sent WITHOUT an id.

Found via trace.log: opencode sends id-less initialize. Server must answer.
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

# variant A: no id field at all (what opencode sent per trace)
proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "initialize"}) + "\n")
proc.stdin.flush()
first = json.loads(proc.stdout.readline())
ok_a = first.get("id") is None and "result" in first and "serverInfo" in first["result"]
print(("PASS" if ok_a else "FAIL") + "  initialize WITHOUT id -> answered with id:null")
print("   ", json.dumps(first)[:120])

# variant B: id:null (same semantic under JSON id typing)
proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": None, "method": "tools/list"}) + "\n")
proc.stdin.flush()
second = json.loads(proc.stdout.readline())
ok_b = "tools" in second.get("result", {})
print(("PASS" if ok_b else "FAIL") + "  id:null tools/list -> answered")

# variant C: real id still works
proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 7, "method": "tools/list"}) + "\n")
proc.stdin.flush()
third = json.loads(proc.stdout.readline())
ok_c = third.get("id") == 7 and "tools" in third.get("result", {})
print(("PASS" if ok_c else "FAIL") + "  normal id=7 tools/list -> answered id=7")

proc.stdin.close()
try:
    proc.wait(timeout=5)
except Exception:
    proc.kill()

ok = ok_a and ok_b and ok_c
print("===", "ALL PASS" if ok else "FAILED", "===")
sys.exit(0 if ok else 1)
