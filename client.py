"""AirMCP Solo client CLI.

Auto-handshake dengan server, lalu interaktif/one-shot.

Examples:
  python client.py tools                       # daftar tools
  python client.py call exec_cmd "dir"         # eksekusi tool
  python client.py resource airmcp://info      # baca resource
  python client.py prompt code-review --code "print(1)"
  python client.py chat                        # chat via LLM bridge + tools
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass


class MCPClient:
    def __init__(self):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        py = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
        if not os.path.exists(py):
            py = sys.executable
        self.proc = subprocess.Popen(
            [py, os.path.join(ROOT, "mcp_server.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", cwd=ROOT, env=env,
        )
        self._id = 0

    def rpc(self, method, params=None):
        self._id += 1
        req = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params:
            req["params"] = params
        self.proc.stdin.write(json.dumps(req) + "\n")
        self.proc.stdin.flush()
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("Server closed")
            msg = json.loads(line)
            if msg.get("id") == self._id and ("error" in msg or "result" in msg):
                return msg

    def close(self):
        try:
            self.proc.stdin.close()
        except Exception:
            pass


def print_result(msg):
    if "error" in msg:
        e = msg["error"]
        print(f"[ERROR {e['code']}] {e['message']}")
        return
    r = msg["result"]
    print(json.dumps(r, indent=2, ensure_ascii=False)[:4000])


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("help", "-h", "--help"):
        print("Usage:")
        print("  python client.py tools")
        print("  python client.py resources")
        print("  python client.py prompts")
        print("  python client.py call <tool_name> [arg=value ...]")
        print("  python client.py resource <uri>")
        print("  python client.py get-prompt <name> [arg=value ...]")
        return 0

    client = MCPClient()
    try:
        cmd = args[0]
        if cmd == "tools":
            resp = client.rpc("tools/list")
            for t in resp["result"]["tools"]:
                print(f"  {t['name']:12} - {t['description']}")

        elif cmd == "resources":
            resp = client.rpc("resources/list")
            for r in resp["result"]["resources"]:
                print(f"  {r['uri']:20} {r['description']}")

        elif cmd == "prompts":
            resp = client.rpc("prompts/list")
            for p in resp["result"]["prompts"]:
                print(f"  {p['name']:22} {p['description']}")

        elif cmd == "call":
            if len(args) < 2:
                print("Usage: python client.py call <tool> [key=value ...]")
                return 1
            tool_args = {}
            for kv in args[2:]:
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    tool_args[k.strip()] = v
            resp = client.rpc("tools/call", {"name": args[1], "arguments": tool_args})
            print_result(resp)

        elif cmd == "resource":
            if len(args) < 2:
                print("Usage: python client.py resource <uri>")
                return 1
            resp = client.rpc("resources/read", {"uri": args[1]})
            print_result(resp)

        elif cmd == "get-prompt":
            if len(args) < 2:
                print("Usage: python client.py get-prompt <name> [key=value ...]")
                return 1
            pargs = {}
            for kv in args[2:]:
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    pargs[k.strip()] = v
            resp = client.rpc("prompts/get", {"name": args[1], "arguments": pargs})
            print(json.dumps(resp["result"], indent=2, ensure_ascii=False)[:4000])

        elif cmd == "chat":
            from llm_bridges.bridges import route_chat, convert_mcp_tools_to_openai

            tools_resp = client.rpc("tools/list")
            openai_tools = convert_mcp_tools_to_openai(tools_resp["result"]["tools"])
            history = []
            print("AirMCP chat (q=quit). LLM: auto route openai->deepseek->hermes")
            while True:
                user = input("you> ").strip()
                if user.lower() in ("q", "quit", "exit"):
                    break
                if not user:
                    continue
                history.append({"role": "user", "content": user})
                system = {"role": "system", "content": (
                    "You are AirMCP assistant. You may call tools via function calling "
                    "when needed: list_files, read_file, exec_cmd, web_fetch. "
                    "Answer concisely.")}
                cur = [system] + history
                for _ in range(5):
                    out = route_chat(cur, tools=openai_tools)
                    tcs = out.get("tool_calls")
                    if tcs:
                        cur.append({"role": "assistant",
                                    "content": out.get("content") or "",
                                    "tool_calls": tcs})
                        for tc in tcs:
                            fname = tc["function"]["name"]
                            fargs = json.loads(tc["function"]["arguments"] or "{}")
                            tr = client.rpc("tools/call", {"name": fname, "arguments": fargs})
                            if "error" in tr:
                                content = json.dumps(tr["error"])
                            else:
                                content = tr["result"]["content"][0]["text"]
                            print(f"  [tool {fname} -> ok]")
                            cur.append({"role": "tool",
                                        "tool_call_id": tc["id"],
                                        "content": content[:8000]})
                    else:
                        break
                content = out.get("content") or "(empty)"
                history.append({"role": "assistant", "content": content})
                print(f"ai ({out.get('provider')})> {content}")

        else:
            print(f"Unknown command: {cmd}")
            return 1
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
