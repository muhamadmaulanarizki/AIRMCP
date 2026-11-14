"""Modern MCP client starts with discovery and uses per-request metadata."""
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
META = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientCapabilities": {},
        "io.modelcontextprotocol/clientInfo": {"name": "modern-test", "version": "1"}}


def main():
    proc = subprocess.Popen([sys.executable, str(ROOT / "mcp_server.py")], cwd=ROOT,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})

    def request(number, method, params=None):
        params = dict(params or {})
        params.setdefault("_meta", META)
        payload = {"jsonrpc": "2.0", "id": number, "method": method,
                   "params": params}
        proc.stdin.write(json.dumps(payload) + "\n")
        proc.stdin.flush()
        response = json.loads(proc.stdout.readline())
        assert response["id"] == number, response
        return response

    try:
        discovery = request(1, "server/discover")["result"]
        assert discovery["resultType"] == "complete"
        assert discovery["supportedVersions"][0] == "2026-07-28"
        assert discovery["_meta"]["io.modelcontextprotocol/serverInfo"]["name"] == "airmcp-solo"

        tools = request(2, "tools/list")["result"]
        assert tools["resultType"] == "complete"
        assert "project_list" in {tool["name"] for tool in tools["tools"]}

        call = request(3, "tools/call", {"name": "project_list", "arguments": {}})["result"]
        assert call["resultType"] == "complete" and "structuredContent" in call

        error = request(4, "tools/list", {"_meta": {**META, "io.modelcontextprotocol/protocolVersion": "2099-01-01"}})
        assert error["error"]["code"] == -32022
        print("PASS: discovery-first modern MCP, complete results, and version errors")
    finally:
        proc.stdin.close()
        proc.wait(timeout=10)


if __name__ == "__main__":
    main()
