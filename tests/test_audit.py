"""Full-function audit: every MCP tool + prompts + resources + all HTTP endpoints.

Run: python tests/test_audit.py
Safe by design: live/network tools are expected to fail or are forced to fast paths.
"""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import shutil
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import mcp_server as srv          # noqa: E402
import providers                  # noqa: E402
import projects                   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

results = []


def rec(name, ok, detail=""):
    results.append((name, bool(ok), detail))


def audit_tools(tmp, dbmid, csvp):
    audit_name = "audit-sandbox"
    audit_root = os.path.join(tmp, audit_name)
    os.makedirs(audit_root, exist_ok=True)
    projects.register(audit_name, audit_root)
    projects.add_note(audit_name, "fixture note")
    projects.save_doc(audit_name, "AUDIT", "# Audit fixture\n")
    ARGS = {
        "list_files": {"path": os.path.join(ROOT, "demo-erp")},
        "read_file": {"path": os.path.join(ROOT, "README.md")},
        "exec_cmd": {"command": "echo audit-ok"},
        "web_fetch": {"url": "https://example.com"},
        "artisan": {"command": "route:list", "path": os.path.join(ROOT, "demo-erp")},
        "composer": {"command": "--version", "path": os.path.join(ROOT, "demo-erp")},
        "db_sqlite": {"db": dbmid, "sql": "select * from t"},
        "csv_stats": {"path": csvp, "group_by": "vendor", "sum_col": "total", "filter": "status=approved"},
        "mysql_query": {"sql": "select 1"},
        "scaffold_crud": {"table": "audit_items", "fields": "nama:string,qty:integer", "path": tmp},
        "project_list": {},
        "project_prompt_list": {"project": audit_name},
        "project_prompt_create": {"project": audit_name, "name": "audit-prompt", "body": "Cek {{x}}", "args": "x"},
        "project_register": {"name": audit_name, "path": audit_root},
        "project_create": {"name": "audit-created", "path": os.path.join(tmp, "audit-created"), "scaffold": False},
        "agent_list": {},
        "agent_create": {"name": "audit-agent", "title": "Audit", "provider": "opencode-go", "model": "opencode-go/glm-5.3", "system": "test"},
        "agent_run": {"agent": "architect", "task": "audit", "simulate": True},
        "agent_delete": {"name": "audit-agent"},
        "orchestrate": {"task": "audit workflow", "team": "architect,coder", "mode": "pipeline", "simulate": True},
        "project_resolve": {"hint": "demo erp"},
        "provider_list": {},
        "provider_create": {"name": "audit-prov", "kind": "http", "base_url": "https://x/v1/chat", "api_key_env": "AUDIT_KEY", "model": "m"},
        "provider_delete": {"name": "audit-prov"},
        "llm_chat": {"prompt": "hi", "provider": "__none__"},
        "route_agent": {"message": "review kode ini"},
        "plan_task": {"task": "buat website ERP integration"},
        "doc_generate": {"project": audit_name, "type": "PRD", "title": "Audit PRD", "save": False},
        "doc_list": {"project": audit_name},
        "doc_read": {"project": audit_name, "type": "AUDIT"},
        "doc_delete": {"project": audit_name, "type": "AUDIT"},
        "doc_build": {"project": audit_name, "type": "PRD", "title": "Audit build"},
        "note_add": {"project": audit_name, "text": "audit note"},
        "note_list": {"project": audit_name},
        "note_update": {"project": audit_name, "index": 0, "text": "updated fixture"},
        "note_delete": {"project": audit_name, "index": 0},
    }
    # tools allowed to fail without deps/network/creds
    EXPECT_ERR = {"llm_chat", "mysql_query", "web_fetch", "artisan", "composer"}
    orig_avail = providers.available_order
    for name, tool in srv.TOOLS.items():
        args = ARGS.get(name, {})
        if name == "doc_generate":
            providers.available_order = lambda: []   # force fast template path
        try:
            out = tool["handler"](args)
            ok = isinstance(out, dict)
            if ok and name == "exec_cmd":
                ok = "audit-ok" in (out.get("output") or "")
            if not ok and name in EXPECT_ERR:
                ok = True
            rec(f"tool:{name}", ok, "" if ok else f"non-dict {type(out)}")
        except Exception as e:  # noqa: BLE001
            if name in EXPECT_ERR:
                rec(f"tool:{name}", True, f"expected: {type(e).__name__}")
            else:
                rec(f"tool:{name}", False, f"{type(e).__name__}: {e}")
        finally:
            providers.available_order = orig_avail
    # cleanup artifacts from audit
    for rel in ((".mcp", "prompts", "audit-prompt.md"),):
        try:
            os.remove(os.path.join(audit_root, *rel))
        except OSError:
            pass


def audit_primitives():
    for pn, p in srv.PROMPTS.items():
        try:
            r = p["handler"]({})
            rec(f"prompt:{pn}", isinstance(r, dict) and "messages" in r)
        except Exception as e:  # noqa: BLE001
            rec(f"prompt:{pn}", False, str(e))
    try:
        r = srv.handle_prompts_get({"name": "demo-erp/analisa-po", "arguments": {"path": "po.csv"}}, None)
        rec("prompt-project:demo-erp/analisa-po", "messages" in r)
    except Exception as e:  # noqa: BLE001
        rec("prompt-project:demo-erp/analisa-po", False, str(e))
    for uri in ("airmcp://info", "airmcp://system"):
        try:
            r = srv.handle_resources_read({"uri": uri}, None)
            rec(f"resource:{uri}", bool(r.get("contents")))
        except Exception as e:  # noqa: BLE001
            rec(f"resource:{uri}", False, str(e))
    try:
        r = srv.handle_resources_read({"uri": "file://" + os.path.join(ROOT, "README.md")}, None)
        rec("resource:file://README", bool(r.get("contents")))
    except Exception as e:  # noqa: BLE001
        rec("resource:file://README", False, str(e))


def audit_http():
    log = os.path.join(ROOT, "audit_http.log")
    proc = subprocess.Popen(
        [sys.executable, "-u", os.path.join(ROOT, "dashboard.py")],
        stdout=open(log, "w", encoding="utf-8"), stderr=subprocess.STDOUT,
        cwd=ROOT, shell=False)
    port = 8765
    try:
        for _ in range(120):
            line = open(log, encoding="utf-8").read()
            if "listening on" in line:
                try:
                    port = int(line.strip().rsplit(":", 1)[1].split()[0])
                except Exception:
                    pass
                break
            time.sleep(0.1)
        base = f"http://127.0.0.1:{port}"

        def get(p):
            with urllib.request.urlopen(base + p, timeout=20) as r:
                return json.loads(r.read().decode())

        def post(p, body):
            req = urllib.request.Request(base + p, method="POST",
                                         data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())

        checks = [
            ("GET /api/server", lambda: "protocolVersion" in get("/api/server")),
            ("GET /api/tools", lambda: len(get("/api/tools").get("tools", [])) >= 20),
            ("GET /api/resources", lambda: len(get("/api/resources").get("resources", [])) >= 3),
            ("GET /api/prompts", lambda: len(get("/api/prompts").get("prompts", [])) >= 3),
            ("GET /api/agents", lambda: len(get("/api/agents").get("agents", [])) >= 5),
            ("GET /api/providers", lambda: len(get("/api/providers").get("providers", [])) >= 1),
            ("GET /api/projects", lambda: "projects" in get("/api/projects")),
            ("GET /api/route", lambda: "agent" in get("/api/route?message=review")),
            ("GET /api/plan", lambda: len(get("/api/plan?message=" + urllib.parse.quote("buat website")).get("steps", [])) >= 1),
            ("GET /api/docs", lambda: "files" in get("/api/docs?project=demo-erp")),
            ("GET /api/doc", lambda: "exists" in get("/api/doc?project=demo-erp&type=PRD")),
            ("GET /api/notes", lambda: "notes" in get("/api/notes?project=demo-erp")),
            ("GET /api/fs", lambda: "dirs" in get("/api/fs?path=")),
            ("POST /api/tools/call", lambda: post("/api/tools/call", {"name": "list_files", "arguments": {"path": os.path.join(ROOT, "demo-erp")}}).get("structuredContent", {}).get("count", 0) >= 1),
            ("POST /api/projects/resolve", lambda: post("/api/projects/resolve", {"hint": "demo erp"}).get("structuredContent", {}).get("resolved") is True),
            ("POST /api/agents/run (sim)", lambda: post("/api/agents/run", {"agent": "architect", "task": "x", "simulate": True}).get("structuredContent", {}).get("simulated") is True),
            ("POST /api/notes", lambda: "added" in post("/api/notes", {"project": "audit-sandbox", "text": "http audit"}).get("structuredContent", {})),
            ("POST /api/orchestrate (sim)", lambda: len(post("/api/orchestrate", {"task": "x", "team": "architect", "simulate": True}).get("structuredContent", {}).get("transcript", [])) == 1),
        ]
        for name, fn in checks:
            try:
                rec(name, fn())
            except Exception as e:  # noqa: BLE001
                rec(name, False, str(e))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except Exception:
            proc.kill()
        try:
            os.remove(log)
        except OSError:
            pass


def main():
    tmp = tempfile.mkdtemp(prefix="audit_")
    snapshots = {}
    for path in (projects.REGISTRY_PATH, projects.STATE_PATH):
        snapshots[path] = open(path, "rb").read() if os.path.exists(path) else None
    dbmid = os.path.join(tmp, "a.sqlite")
    c = sqlite3.connect(dbmid)
    c.execute("create table t(id int, name text)")
    c.execute("insert into t values(1,'x')")
    c.commit()
    c.close()
    csvp = os.path.join(ROOT, "demo-erp", "purchase_orders.csv")

    try:
        audit_tools(tmp, dbmid, csvp)
        audit_primitives()
        audit_http()

        passed = sum(1 for _, ok, _ in results if ok)
        for name, ok, detail in results:
            line = ("PASS " if ok else "FAIL ") + name
            if detail and not ok:
                line += "  -> " + detail
            elif detail:
                line += "  (" + detail + ")"
            print(line)
        print(f"=== AUDIT: {passed}/{len(results)} passed ===")
        return 0 if passed == len(results) else 1
    finally:
        for path, content in snapshots.items():
            if content is None:
                try:
                    os.remove(path)
                except OSError:
                    pass
            else:
                with open(path, "wb") as file:
                    file.write(content)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
