"""Unit + integration tests for orchestrator.py and agents.json (dynamic)."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import orchestrator  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

results = []


def check(name, cond):
    results.append((name, bool(cond)))


def main():
    path = orchestrator.AGENTS_PATH
    backup = open(path, encoding="utf-8").read() if os.path.exists(path) else None
    saved_key = os.environ.pop("OPENAI_API_KEY", None)
    orig_avail = orchestrator.available_providers
    orchestrator.available_providers = lambda: []  # deterministic: no live call
    try:
        # --- agent CRUD
        base = orchestrator.load_agents()
        check("agents present", {"architect", "coder", "reviewer", "tester"} <= set(base))
        orchestrator.create_agent("t1", "T1", "deepseek", "sys", True)
        check("create agent", "t1" in orchestrator.load_agents())
        check("get agent", orchestrator.get_agent("t1")["title"] == "T1")
        orchestrator.delete_agent("t1")
        check("delete agent", "t1" not in orchestrator.load_agents())
        try:
            orchestrator.delete_agent("t1")
            check("delete missing raises", False)
        except ValueError:
            check("delete missing raises", True)
        try:
            orchestrator.create_agent("bad name!", None, None, None)
            check("create slug validated", False)
        except ValueError:
            check("create slug validated", True)

        # --- resolve_project
        check("resolve exact", orchestrator.resolve_project("demo-erp")["project"] == "demo-erp")
        fuzzy = orchestrator.resolve_project("proyek demo erp")
        check("resolve fuzzy hits demo-erp", fuzzy and fuzzy["project"] == "demo-erp")
        pathres = orchestrator.resolve_project(os.path.join(ROOT, "demo-erp"))
        check("resolve by path", pathres and pathres["match"] in ("exact-path", "path"))
        check("resolve none", orchestrator.resolve_project("zzz-tidak-ada-xyz") is None)

        # --- run_agent (simulation)
        r = orchestrator.run_agent("architect", "buat fitur", allow_simulation=True)
        check("run_agent simulated", r["simulated"] is True and "SIMULASI" in r["content"])
        check("run_agent provider sim", r["provider"] == "simulation")
        try:
            orchestrator.run_agent("nope", "x", allow_simulation=True)
            check("run_agent unknown raises", False)
        except ValueError:
            check("run_agent unknown raises", True)

        # --- orchestrate modes (forced simulation)
        p = orchestrator.orchestrate("tugas A", team="architect,coder,reviewer",
                                     mode="pipeline", allow_simulation=True)
        check("pipeline length", len(p["transcript"]) == 3)
        check("pipeline simulated", p["simulated"] is True)
        statuses = []
        orchestrator.orchestrate("status", team="architect", mode="pipeline",
                                 allow_simulation=True, on_status=statuses.append)
        check("orchestrate emits turn start", statuses == [{
            "phase": "start", "agent": "architect", "title": "Technical Lead",
            "provider": "opencode",
        }])

        d = orchestrator.orchestrate("tugas B", team="architect,coder", mode="debate",
                                     rounds=2, allow_simulation=True)
        check("debate length = team*rounds", len(d["transcript"]) == 4)

        s = orchestrator.orchestrate("tugas C", team="architect,coder", mode="supervisor",
                                     allow_simulation=True)
        check("supervisor lead appears twice", [t["agent"] for t in s["transcript"]] ==
              ["architect", "coder", "architect"])

        try:
            orchestrator.orchestrate("x", team="ghost", allow_simulation=True)
            check("orchestrate unknown agent raises", False)
        except ValueError:
            check("orchestrate unknown agent raises", True)

        try:
            orchestrator.orchestrate("", team="architect", allow_simulation=True)
            check("orchestrate empty task raises", False)
        except ValueError:
            check("orchestrate empty task raises", True)

        try:
            orchestrator.orchestrate("x", team="architect", mode="weird", allow_simulation=True)
            check("orchestrate bad mode raises", False)
        except ValueError:
            check("orchestrate bad mode raises", True)

        # --- no provider + allow_simulation False -> RuntimeError
        try:
            orchestrator.run_agent("architect", "x", allow_simulation=False)
            check("no provider raises", False)
        except RuntimeError:
            check("no provider raises", True)

        # --- tool-calling loop with a faked model
        import llm_bridges.bridges as bridges
        orig_route = bridges.route_chat
        os.environ["OPENAI_API_KEY"] = "test-key"
        seen = []

        def fake_route(messages, tools=None, preferred=None, model=None):
            if not any(m.get("role") == "tool" for m in messages):
                return {"content": "", "provider": "fake", "tool_calls": [{
                    "id": "1", "type": "function",
                    "function": {"name": "list_files", "arguments": json.dumps({"path": ROOT})}}]}
            return {"content": "selesai", "provider": "fake", "tool_calls": None}

        bridges.route_chat = fake_route
        orchestrator.available_providers = lambda: ["openai"]
        try:
            def exec_tool(name, args):
                seen.append((name, args))
                return {"entries": [{"name": "x"}]}

            r2 = orchestrator.run_agent("architect", "list file",
                                        tool_executor=exec_tool,
                                        tools_spec=[{"type": "function",
                                                     "function": {"name": "list_files", "parameters": {}}}])
            check("tool executor called", seen and seen[0][0] == "list_files")
            check("tool_call recorded", r2["tool_calls"] and r2["tool_calls"][0]["name"] == "list_files")
            check("final content", r2["content"] == "selesai")
            check("not simulated", r2["simulated"] is False)
        finally:
            bridges.route_chat = orig_route
            orchestrator.available_providers = lambda: []
            os.environ.pop("OPENAI_API_KEY", None)
    finally:
        orchestrator.available_providers = orig_avail
        if saved_key is not None:
            os.environ["OPENAI_API_KEY"] = saved_key
        if backup is not None:
            with open(path, "w", encoding="utf-8") as f:
                f.write(backup)

    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(("PASS " if ok else "FAIL ") + name)
    print(f"=== orchestrator: {passed}/{len(results)} passed ===")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
