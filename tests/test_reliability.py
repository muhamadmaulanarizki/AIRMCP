import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import jsonrpc
import mcp_server as server
import dashboard
import security as security_policy

class ReliabilityTests(unittest.TestCase):
    def test_parser_recovers(self):
        source = io.StringIO("\n" * 3000 + 'broken\n[]\n' + json.dumps({"jsonrpc":"2.0","id":1,"method":"ping"}) + "\n")
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(jsonrpc.read_message(source)["id"], 1)
        self.assertEqual([json.loads(x)["error"]["code"] for x in output.getvalue().splitlines()], [-32700, -32600])

    def test_invalid_arguments(self):
        for value in ([], False, "bad", 1, None):
            with self.assertRaises(ValueError):
                server.handle_tools_call({"name":"list_files","arguments":value}, {})

    def test_execution_failure(self):
        result = server.handle_tools_call({"name":"read_file","arguments":{"path":"__missing_reliability_test__"}}, {})
        self.assertTrue(result["isError"])
        self.assertTrue(dashboard._unwrap({"result":result})["isError"])

    def test_nonzero_exit(self):
        result = server.handle_tools_call({"name":"exec_cmd","arguments":{"command":"exit 7"}}, {})
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"]["exit_code"], 7)

    def test_unwrap_multiple_blocks(self):
        result = dashboard._unwrap({"result":{"content":[{"type":"text","text":"one"},{"type":"text","text":"two"}],"isError":True}})
        self.assertEqual(result["text"], "one\ntwo")
        self.assertTrue(result["isError"])

    def test_ping(self):
        self.assertEqual(server.HANDLERS["ping"]({}, {}), {})

    def test_production_blocks_dangerous_tool(self):
        with patch.dict(os.environ, {"AIRMCP_PRODUCTION":"1", "AIRMCP_ALLOWED_DANGEROUS_TOOLS":""}):
            result = server.handle_tools_call({"name":"exec_cmd","arguments":{"command":"echo blocked"}}, {})
            visible = server.HANDLERS["tools/list"]({}, {})["tools"]
        self.assertTrue(result["isError"])
        self.assertIn("dinonaktifkan", result["content"][0]["text"])
        self.assertNotIn("exec_cmd", {tool["name"] for tool in visible})

    def test_production_path_sandbox_and_sensitive_files(self):
        with tempfile.TemporaryDirectory() as root:
            normal = Path(root, "readme.txt")
            normal.write_text("ok", encoding="utf-8")
            secret = Path(root, ".env")
            secret.write_text("SECRET=x", encoding="utf-8")
            env = {"AIRMCP_PRODUCTION":"1", "AIRMCP_ALLOWED_ROOTS":root}
            with patch.dict(os.environ, env):
                self.assertEqual(security_policy.ensure_allowed_path(normal), str(normal.resolve()))
                with self.assertRaises(PermissionError):
                    security_policy.ensure_allowed_path(secret)

    def test_production_rejects_private_web_target(self):
        with patch.dict(os.environ, {"AIRMCP_PRODUCTION":"1", "AIRMCP_ALLOW_PRIVATE_NETWORK":"0"}):
            with self.assertRaises(PermissionError):
                security_policy.ensure_safe_url("http://127.0.0.1/private")

class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import threading
        dashboard.pool = dashboard.ClientPool(size=2)
        cls.server = dashboard.QuietServer(("127.0.0.1", 0), dashboard.Handler)
        cls.url = "http://127.0.0.1:" + str(cls.server.server_port)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        dashboard.pool.close_all()

    def request(self, path, body=None):
        import urllib.request
        req = urllib.request.Request(self.url + path, data=body,
            headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read()

    def test_discovery(self):
        for path, key in (("/api/server","protocolVersion"), ("/api/tools","tools"),
                          ("/api/resources","resources"), ("/api/prompts","prompts")):
            self.assertIn(key, json.loads(self.request(path)))
        self.assertIn(b"Navigasi utama", self.request("/"))

    def test_reject_non_object(self):
        import urllib.error
        for body in (b"[]", b"null", b"false", b"bad", b"\xff"):
            with self.assertRaises(urllib.error.HTTPError) as raised:
                self.request("/api/tools/call", body)
            self.assertEqual(raised.exception.code, 400)

    def test_error_survives_http(self):
        body = json.dumps({"name":"read_file","arguments":{"path":"__missing_reliability_test__"}}).encode()
        result = json.loads(self.request("/api/tools/call", body))
        self.assertTrue(result["isError"])
        self.assertIn("__missing_reliability_test__", result["text"])

    def test_stream_has_tool_access(self):
        from unittest.mock import patch
        def fake(*args, **kwargs):
            self.assertTrue(callable(kwargs["tool_executor"]))
            self.assertTrue(kwargs["tools_spec"])
            return {"transcript":[], "simulated":True}
        with patch("orchestrator.orchestrate", side_effect=fake):
            result = self.request("/api/orchestrate/stream", b'{"task":"test","simulate":true}')
        self.assertEqual(json.loads(result)["type"], "done")

    def test_production_dashboard_authentication(self):
        import urllib.error
        import urllib.request
        env = {"AIRMCP_PRODUCTION":"1", "AIRMCP_DASHBOARD_TOKEN":"test-production-token"}
        with patch.dict(os.environ, env):
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(self.url + "/api/server", timeout=10)
            self.assertEqual(raised.exception.code, 401)
            req = urllib.request.Request(self.url + "/api/server", headers={"X-AirMCP-Token":"test-production-token"})
            with urllib.request.urlopen(req, timeout=10) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    def test_production_rate_limit(self):
        import urllib.error
        import urllib.request
        env = {"AIRMCP_PRODUCTION":"1", "AIRMCP_DASHBOARD_TOKEN":"rate-token",
               "AIRMCP_RATE_LIMIT_PER_MINUTE":"1"}
        dashboard.rate_limiter.clear()
        with patch.dict(os.environ, env):
            req = urllib.request.Request(self.url + "/api/server", headers={"X-AirMCP-Token":"rate-token"})
            with urllib.request.urlopen(req, timeout=10) as response:
                self.assertEqual(response.status, 200)
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(req, timeout=10)
            self.assertEqual(raised.exception.code, 429)
            self.assertEqual(raised.exception.headers["Retry-After"], "60")
        dashboard.rate_limiter.clear()

if __name__ == "__main__":
    unittest.main()
