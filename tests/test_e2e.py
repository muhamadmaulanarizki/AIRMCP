"""End-to-end integration test: drives mcp_server.py over its stdin/stdout.

Run: python tests/test_e2e.py
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PASS, FAIL = "\u2705 PASS", "\u274C FAIL"
results = []


def rpc(msg):
    return json.dumps(msg)


def main():
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "mcp_server.py")],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", cwd=ROOT, env=env, shell=False,
    )

    def send(line):
        proc.stdin.write(line + "\n")
        proc.stdin.flush()

    def recv(expected_id=None):
        while True:
            line = proc.stdout.readline()
            if not line:
                return None
            msg = json.loads(line)
            if expected_id is not None and msg.get("id") != expected_id:
                continue
            return msg

    # 1. initialize handshake
    send(rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"clientInfo": {"name": "eit", "version": "0"}}}))
    resp = recv(1)
    ok = resp and resp["result"]["protocolVersion"] == "2026-07-28" and "capabilities" in resp["result"]
    results.append(("initialize handshake", ok, resp))
    print(f"{PASS if ok else FAIL} initialize -> protocolVersion={resp['result']['protocolVersion']}, "
          f"capabilities={list(resp['result']['capabilities'].keys())}")

    # 2. tools/list
    send(rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}))
    resp = recv(2)
    names = [t["name"] for t in resp["result"]["tools"]]
    ok = set(names) >= {"list_files", "read_file", "exec_cmd", "web_fetch"}
    results.append(("tools/list", ok, resp))
    print(f"{PASS if ok else FAIL} tools/list -> {names}")

    # 3. tools/call list_files
    send(rpc({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
              "params": {"name": "list_files", "arguments": {"path": ROOT}}}))
    resp = recv(3)
    entry_names = [e["name"] for e in resp["result"]["structuredContent"]["entries"]]
    ok = "mcp_server.py" in entry_names
    results.append(("tools/call list_files", ok, resp))
    print(f"{PASS if ok else FAIL} tools/call list_files -> found files: {entry_names[:4]} ...")

    # 4. tools/call exec_cmd
    send(rpc({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
              "params": {"name": "exec_cmd", "arguments": {"command": "echo airmcp-e2e"}}}))
    resp = recv(4)
    ok = "airmcp-e2e" in resp["result"]["structuredContent"]["output"]
    results.append(("tools/call exec_cmd", ok, resp))
    print(f"{PASS if ok else FAIL} tools/call exec_cmd -> output={resp['result']['structuredContent']['output']!r}")

    # 5. tools/call missing required arg -> error -32602
    send(rpc({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
              "params": {"name": "read_file", "arguments": {}}}))
    resp = recv(5)
    ok = resp.get("error", {}).get("code") == -32602
    results.append(("tools/call invalid params error", ok, resp))
    print(f"{PASS if ok else FAIL} invalid params -> error code {resp['error']['code']}: {resp['error']['message']}")

    # 6. unknown method -> -32601
    send(rpc({"jsonrpc": "2.0", "id": 6, "method": "totally/unknown"}))
    resp = recv(6)
    ok = resp.get("error", {}).get("code") == -32601
    results.append(("method not found", ok, resp))
    print(f"{PASS if ok else FAIL} unknown method -> {resp['error']['code']}")

    # 7. resources/read airmcp://info
    send(rpc({"jsonrpc": "2.0", "id": 7, "method": "resources/read",
              "params": {"uri": "airmcp://info"}}))
    resp = recv(7)
    info = json.loads(resp["result"]["contents"][0]["text"])
    ok = info["server"]["name"] == "airmcp-solo"
    results.append(("resources/read info", ok, resp))
    print(f"{PASS if ok else FAIL} resources/read airmcp://info -> server={info['server']['name']}")

    # 8. resources/read file:// README
    readme = os.path.join(ROOT, "README.md")
    send(rpc({"jsonrpc": "2.0", "id": 8, "method": "resources/read",
              "params": {"uri": "file://" + readme}}))
    resp = recv(8)
    ok = resp and "result" in resp and "contents" in resp["result"]
    results.append(("resources/read file://", ok, resp))
    print(f"{PASS if ok else FAIL} resources/read file:// -> {str(resp)[:80]}")

    # 9. prompts/list
    send(rpc({"jsonrpc": "2.0", "id": 9, "method": "prompts/list"}))
    resp = recv(9)
    pnames = [p["name"] for p in resp["result"]["prompts"]]
    ok = set(pnames) >= {"code-review", "system-instructions", "few-shot"}
    results.append(("prompts/list", ok, resp))
    print(f"{PASS if ok else FAIL} prompts/list -> {pnames}")

    # 10. prompts/get code-review
    send(rpc({"jsonrpc": "2.0", "id": 10, "method": "prompts/get",
              "params": {"name": "code-review", "arguments": {"code": "print(1)"}}}))
    resp = recv(10)
    ok = "Review the following code" in resp["result"]["messages"][0]["content"]
    results.append(("prompts/get code-review", ok, resp))
    print(f"{PASS if ok else FAIL} prompts/get -> {resp['result']['messages'][0]['content'][:60]}...")

    # 10b. prompts/get per-project template (demo-erp/analisa-po)
    send(rpc({"jsonrpc": "2.0", "id": 101, "method": "prompts/get",
              "params": {"name": "demo-erp/analisa-po",
                         "arguments": {"path": "purchase_orders.csv"}}}))
    resp = recv(101)
    body = json.dumps(resp)
    ok = bool(resp) and "result" in resp and "purchase_orders.csv" in body and "{{path}}" not in body
    results.append(("prompts/get project prompt", ok, resp))
    print(f"{PASS if ok else FAIL} prompts/get demo-erp/analisa-po -> {body[:80]}...")

    # 11. elicitation/create
    send(rpc({"jsonrpc": "2.0", "id": 11, "method": "elicitation/create",
              "params": {"question": "Proceed with destructive action?", "choices": ["yes", "no"]}}))
    resp = recv(11)
    ok = resp["result"]["elicitId"] and resp["result"]["choices"] == ["yes", "no"]
    results.append(("elicitation/create", ok, resp))
    print(f"{PASS if ok else FAIL} elicitation -> id={resp['result']['elicitId']}, Q={resp['result']['question']!r}")

    # 12. subscriptions/listen
    send(rpc({"jsonrpc": "2.0", "id": 12, "method": "subscriptions/listen",
              "params": {"notifications": ["toolsListChanged"]}}))
    resp = recv(12)
    ok = "toolsListChanged" in resp["result"]["accepted"]
    results.append(("subscriptions/listen", ok, resp))
    print(f"{PASS if ok else FAIL} subscriptions -> accepted={resp['result']['accepted']}")

    # close
    proc.stdin.close()
    proc.wait(timeout=10)

    failed = [name for name, ok, _ in results if not ok]
    print()
    print(f"=== {len(results) - len(failed)}/{len(results)} passed ===")
    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
