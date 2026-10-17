"""AirMCP - Solo MCP Server with all primitives.

Tools | Resources | Prompts | Notifications | Elicitation
STDIO transport, JSON-RPC 2.0, MCP spec 2026-07-28.
"""
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

import json
import base64
import mimetypes
from urllib.parse import urlparse, unquote

from jsonrpc import (
    read_message, write_message, make_response, make_error, make_notification,
    METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR, INVALID_REQUEST,
)

import projects
import orchestrator
import providers
import documents
import security as security_policy

PROTOCOL_VERSION = "2026-07-28"
SERVER_INFO = {"name": "airmcp-solo", "version": "1.0.0"}
ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "icons")


def icon_data_uri(name):
    path = os.path.join(ICONS_DIR, name)
    if not os.path.exists(path):
        return None
    mime = mimetypes.guess_type(path)[0] or "image/svg+xml"
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def _icons(icon):
    return [icon] if icon and icon.get("source") else None


# ---------------------------------------------------------------- tools
def tool_list_files(args):
    path = (args.get("path") or "").strip() or "."
    path = security_policy.ensure_allowed_path(path)
    if not os.path.isdir(path):
        raise ValueError(f"Bukan folder / tidak ditemukan: {path}")
    try:
        limit = int(args.get("limit") or 500)
    except (TypeError, ValueError):
        limit = 500
    limit = max(1, min(limit, 2000))
    try:
        names = sorted(os.listdir(path), key=str.lower)
    except OSError as e:
        raise ValueError(f"Gagal membaca folder: {e}")
    total = len(names)
    entries = []
    for e in names[:limit]:
        full = os.path.join(path, e)
        kind = "dir" if os.path.isdir(full) else "file"
        try:
            size = os.path.getsize(full) if kind == "file" else None
        except OSError:
            size = None
        entries.append({"name": e, "type": kind, "size": size})
    return {"path": path, "count": len(entries), "total": total,
            "truncated": total > len(entries), "entries": entries}


def tool_read_file(args):
    path = (args.get("path") or "").strip()
    if not path:
        raise ValueError("Missing required arg: path")
    path = security_policy.ensure_allowed_path(path)
    if not os.path.isfile(path):
        raise ValueError(f"File tidak ditemukan: {path}")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read(100_000)
    return {"path": path, "content": content}


def tool_exec_cmd(args):
    import subprocess
    cmd = args.get("command")
    if not cmd:
        raise ValueError("Missing required arg: command")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    out = (r.stdout or "") + (("\n[stderr]\n" + r.stderr) if r.stderr else "")
    return {"exit_code": r.returncode, "output": out.strip()[:50_000]}


def tool_web_fetch(args):
    url = args.get("url")
    if not url:
        raise ValueError("Missing required arg: url")
    url = security_policy.ensure_safe_url(url)
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "AirMCP/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read(200_000).decode("utf-8", errors="replace")
    return {"url": url, "status": getattr(resp, "status", 200), "length": len(body), "body": body}


def _run_in_dir(cmd, cwd, timeout=120):
    import subprocess
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    return {
        "cwd": cwd,
        "exit_code": r.returncode,
        "stdout": (r.stdout or "").strip()[:50_000],
        "stderr": (r.stderr or "").strip()[:20_000],
    }


def tool_artisan(args):
    """Run a php artisan command inside a Laravel project (ERP dev helper)."""
    cmd = (args.get("command") or "").strip()
    path = security_policy.ensure_allowed_path(args.get("path") or ".")
    if not cmd:
        raise ValueError("Missing command, e.g. 'migrate', 'route:list', 'make:model X --migration'")
    allowed_creators = ("make", "migrate", "db:", "route:", "config:", "test", "tinker", "queue:", "sche")
    if not cmd.startswith(allowed_creators):
        raise ValueError("Disallowed artisan command prefix (safety): " + cmd.split()[0])
    return _run_in_dir(f'php artisan {cmd}', path, timeout=180)


def tool_composer(args):
    cmd = (args.get("command") or "install").strip()
    path = security_policy.ensure_allowed_path(args.get("path") or ".")
    dangerous = ("remove", "require")
    if any(cmd.startswith(d) and ";" in cmd for d in dangerous):
        raise ValueError("Chained commands not allowed")
    return _run_in_dir(f'composer {cmd}', path, timeout=300)


def tool_db_sqlite(args):
    """Run a read-only SQL query on a SQLite file (ERP local data exploration)."""
    import sqlite3
    db = args.get("db")
    sql = (args.get("sql") or "").strip().rstrip(";")
    if not db or not sql:
        raise ValueError("Need db (path to .sqlite) and sql")
    db = security_policy.ensure_allowed_path(db)
    head = sql.split()[0].upper()
    if head not in ("SELECT", "PRAGMA", "EXPLAIN", "WITH"):
        raise ValueError("Read-only tool: only SELECT / PRAGMA / EXPLAIN / WITH allowed")
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(sql)
        rows = [dict(r) for r in cur.fetchmany(200)]
        cols = list(rows[0].keys()) if rows else []
        return {"db": db, "columns": cols, "row_count": len(rows), "rows": rows}
    finally:
        conn.close()


def tool_csv_stats(args):
    """Summarize a CSV file: optionally filter rows and group/aggregate columns.

    Built as a demo of 'making a tool using MCP itself'.
    Example: path=purchase_orders.csv group_by=vendor sum_col=total filter=status=approved
    """
    import csv
    path = args.get("path")
    group_by = args.get("group_by")
    sum_col = args.get("sum_col")
    filt = args.get("filter")
    if not path:
        raise ValueError("Missing required arg: path")
    path = security_policy.ensure_allowed_path(path)
    with open(path, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if filt:
        fkey, _, fval = filt.partition("=")
        rows = [r for r in rows if r.get(fkey, "").strip().lower() == fval.strip().lower()]
    summary = []
    if group_by:
        groups = {}
        for r in rows:
            g = r.get(group_by, "?")
            slot = groups.setdefault(g, {"count": 0, "sum": 0.0})
            slot["count"] += 1
            if sum_col:
                try:
                    slot["sum"] += float(str(r.get(sum_col, "0") or 0))
                except ValueError:
                    pass
        summary = [{"group": k, **v} for k, v in groups.items()]
    else:
        summary = rows
    return {
        "path": path,
        "rows_after_filter": len(rows),
        "summary": summary,
    }


def tool_mysql_query(args):
    """Read-only SQL against a MySQL server (ERP production/dev DB exploration)."""
    sql = (args.get("sql") or "").strip().rstrip(";")
    if not sql:
        raise ValueError("Missing required arg: sql")
    head = sql.split()[0].upper()
    if head not in ("SELECT", "SHOW", "DESCRIBE", "DESC", "EXPLAIN", "WITH"):
        raise ValueError("Read-only tool: only SELECT / SHOW / DESCRIBE / EXPLAIN / WITH allowed")
    if ";" in sql:
        raise ValueError("Only a single statement allowed")
    try:
        import pymysql
    except ImportError:
        raise RuntimeError("pymysql not installed: run venv's pip install pymysql")
    conn = pymysql.connect(
        host=args.get("host") or os.environ.get("MYSQL_HOST", "127.0.0.1"),
        port=int(args.get("port") or os.environ.get("MYSQL_PORT", "3306")),
        user=args.get("user") or os.environ.get("MYSQL_USER", "root"),
        password=args.get("password") or os.environ.get("MYSQL_PASSWORD", ""),
        database=args.get("database") or os.environ.get("MYSQL_DATABASE"),
        connect_timeout=10,
    )
    try:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchmany(200)
        data = [dict(zip(cols, [str(v) for v in r])) for r in rows] if cols else []
        return {"columns": cols, "row_count": len(data), "rows": data}
    finally:
        conn.close()


_TYPE_MAP = {
    "string": lambda n, t: f"$table->string('{n}'{(f', {t}') if t else ''})",
    "integer": lambda n, t: f"$table->integer('{n}')",
    "decimal": lambda n, t: f"$table->decimal('{n}', 15, 2)",
    "text": lambda n, t: f"$table->text('{n}')",
    "boolean": lambda n, t: f"$table->boolean('{n}')",
    "date": lambda n, t: f"$table->date('{n}')",
    "datetime": lambda n, t: f"$table->dateTime('{n}')",
    "foreign_id": lambda n, t: f"$table->foreignId('{n}')",
}


def tool_scaffold_crud(args):
    """Generate Laravel scaffold (model + controller + migration + routes snippet).

    ERP dev accelerator: pass a table + fields, get ready CRUD files.
    Refuses to overwrite existing files unless force=true.
    """
    import re
    table = (args.get("table") or "").strip().lower()
    path = security_policy.ensure_allowed_path(args.get("path") or ".")
    fields_raw = args.get("fields") or ""
    force = bool(args.get("force"))
    if not re.fullmatch(r"[a-z][a-z0-9_]*", table or ""):
        raise ValueError("table must be snake_case, e.g. purchase_orders")
    if not table.endswith("s"):
        table += "s"
    class_name = "".join(w.capitalize() for w in table.split("_"))
    if len(class_name) > 2 and class_name.endswith("s") and not class_name.endswith("ss"):
        class_name = class_name[:-1]
    fields = []
    for part in fields_raw.split(","):
        part = part.strip()
        if not part:
            continue
        name, _, ftype = part.partition(":")
        name = name.strip()
        ftype = (ftype or "string").strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            raise ValueError(f"bad field name: {name}")
        if ftype.split("(", 1)[0] not in _TYPE_MAP:
            raise ValueError(f"unsupported type: {ftype} (use {list(_TYPE_MAP)})")
        fields.append((name, ftype))

    model_dir = os.path.join(path, "app", "Models")
    ctrl_dir = os.path.join(path, "app", "Http", "Controllers")
    mig_dir = os.path.join(path, "database", "migrations")
    route_dir = os.path.join(path, "routes")
    created, skipped = [], []

    def write(rel, content):
        full = os.path.join(path, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        if os.path.exists(full) and not force:
            skipped.append(rel)
            return
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        created.append(rel)

    stamp = "2026_01_01_000000"
    # --- migration
    cols = "\n            ".join(_TYPE_MAP[t](n, "") + ";" for n, t in fields)
    mig = f"""<?php

use Illuminate\\Database\\Migrations\\Migration;
use Illuminate\\Database\\Schema\\Blueprint;
use Illuminate\\Support\\Facades\\Schema;

return new class extends Migration
{{
    public function up(): void
    {{
        Schema::create('{table}', function (Blueprint $table) {{
            $table->id();
            {cols}
            $table->timestamps();
        }});
    }}

    public function down(): void
    {{
        Schema::dropIfExists('{table}');
    }}
}};
"""
    write(f"database{os.sep}migrations{os.sep}{stamp}_create_{table}_table.php", mig)

    # --- model
    fillable = ", ".join(f"'{n}'" for n, t in fields)
    cast_map = {"decimal": "decimal:2", "boolean": "boolean",
                "datetime": "datetime", "date": "date", "integer": "integer"}
    casts = ", ".join(
        f"'{n}' => '{cast_map[t]}'" for n, t in fields if t in cast_map
    )
    model = f"""<?php

namespace App\\Models;

use Illuminate\\Database\\Eloquent\\Model;

class {class_name} extends Model
{{
    protected $fillable = [{fillable}];

    protected $casts = [{casts}];
}}
"""
    write(f"app{os.sep}Models{os.sep}{class_name}.php", model)

    # --- controller
    singular = class_name
    ctrl = f"""<?php

namespace App\\Http\\Controllers;

use App\\Models\\{singular};
use Illuminate\\Http\\Request;

class {singular}Controller extends Controller
{{
    public function index()
    {{
        return response()->json({singular}::latest()->paginate(25));
    }}

    public function store(Request $request)
    {{
        $data = $request->validate([ /* rules untuk: {fillable} */ ]);
        return response()->json({singular}::create($data), 201);
    }}

    public function show({singular} $po)
    {{
        return response()->json($po);
    }}

    public function update(Request $request, {singular} $po)
    {{
        $data = $request->validate([ /* rules untuk: {fillable} */ ]);
        $po->update($data);
        return response()->json($po);
    }}

    public function destroy({singular} $po)
    {{
        $po->delete();
        return response()->noContent();
    }}
}}
"""
    write(f"app{os.sep}Http{os.sep}Controllers{os.sep}{class_name}Controller.php", ctrl)

    # --- routes snippet
    routes = f"""<?php

use App\\Http\\Controllers\\{class_name}Controller;
use Illuminate\\Support\\Facades\\Route;

Route::apiResource('{table}', {class_name}Controller::class);
"""
    write(f"routes{os.sep}{table}_routes_snippet.php", routes)

    print_count = {"created": created, "skipped": skipped}
    return {
        "table": table,
        "class": class_name,
        "fields": [f"{n}:{t}" for n, t in fields],
        "created_files": created,
        "skipped_existing": skipped,
        "note": "Copy the routes snippet into routes/api.php manually if desired.",
    }


def tool_project_list(args):
    """List registered projects and how many prompt templates each has."""
    return {"projects": projects.list_projects(), "active_project": projects.get_active()}


def tool_project_create(args):
    """Buat folder project baru (+ scaffold, prompt, dokumen) lalu daftarkan & jadikan aktif."""
    path = args.get("path")
    if path:
        path = security_policy.ensure_allowed_path(path, allow_missing=True)
    return projects.create_project(
        args.get("name"), path,
        scaffold=args.get("scaffold", True) is not False,
        stack=args.get("stack"))


def tool_project_select(args):
    """Tandai project aktif (dipakai default oleh agent_run/orchestrate)."""
    return projects.set_active(args.get("project"))


def tool_project_active(args):
    """Tampilkan project aktif saat ini."""
    name = projects.get_active()
    return {"active_project": name, "path": projects.project_dir(name) if name else None}


def tool_project_prompt_list(args):
    """List per-project prompt templates (name '<project>/<slug>')."""
    return {"prompts": projects.prompt_defs(args.get("project"))}


def tool_project_prompt_create(args):
    """Create a per-project prompt template file under <project>/.mcp/prompts/."""
    return projects.create_prompt(
        project=args.get("project"),
        name=args.get("name"),
        body=args.get("body"),
        title=args.get("title"),
        description=args.get("description"),
        args=args.get("args"),
    )


def tool_project_register(args):
    """Register a project root so its .mcp/prompts/ folder is discovered."""
    path = security_policy.ensure_allowed_path(args.get("path"))
    return projects.register(args.get("name"), path)


# ------------------------------------------------------- agent orchestration
_ORCH_EXCLUDE = {"orchestrate", "agent_run", "agent_create", "agent_delete",
                 "provider_create", "provider_delete", "project_register", "llm_chat",
                 "project_create", "project_select", "doc_generate",
                 "note_delete", "doc_delete"}


def _local_tool_executor(name, args):
    """Run an MCP tool locally (used by agents that have tool access)."""
    tool = TOOLS.get(name)
    if not tool:
        raise ValueError("tool tidak dikenal: " + str(name))
    security_policy.ensure_tool_allowed(name)
    for req in tool.get("inputSchema", {}).get("required", []):
        if req not in (args or {}):
            raise ValueError("Missing required argument: " + req)
    return tool["handler"](args or {})


def _tools_spec():
    from llm_bridges.bridges import convert_mcp_tools_to_openai
    defs = [{k: v for k, v in t.items() if k != "handler"}
            for t in TOOLS.values()
            if t["name"] not in _ORCH_EXCLUDE and security_policy.tool_allowed(t["name"])]
    return convert_mcp_tools_to_openai(defs)


def _visible_tool_defs():
    return [t for t in TOOLS.values() if security_policy.tool_allowed(t["name"])]


def tool_agent_list(args):
    """List configured agents and which LLM providers have keys."""
    return {"agents": orchestrator.agent_defs(),
            "providers_available": orchestrator.available_providers()}


def tool_agent_create(args):
    """Create/update an agent definition (name, provider, model, system, tools)."""
    return orchestrator.create_agent(
        args.get("name"), title=args.get("title"), provider=args.get("provider"),
        system=args.get("system"), tools=args.get("tools", True), model=args.get("model"))


def tool_agent_run(args):
    """Run a single agent on a task, with auto project-path resolution."""
    simulate = True if args.get("simulate") else None
    return orchestrator.run_agent(
        args.get("agent"), args.get("task"), project=args.get("project"),
        path=args.get("path"), context=args.get("context"),
        tool_executor=_local_tool_executor, tools_spec=_tools_spec(),
        allow_simulation=simulate)


def tool_orchestrate(args):
    """Run a team of agents on a project (pipeline / debate / supervisor)."""
    simulate = True if args.get("simulate") else None
    return orchestrator.orchestrate(
        args.get("task"), project=args.get("project"), path=args.get("path"),
        team=args.get("team"), mode=args.get("mode", "pipeline"),
        rounds=args.get("rounds", 2),
        tool_executor=_local_tool_executor, tools_spec=_tools_spec(),
        allow_simulation=simulate)


def tool_project_resolve(args):
    """Auto-pick the best project + path matching a free-text hint."""
    res = orchestrator.resolve_project(args.get("hint"))
    if not res:
        return {"resolved": False, "hint": args.get("hint"),
                "projects": [p["project"] for p in projects.list_projects()]}
    return {"resolved": True, **res}


def tool_provider_list(args):
    """List dynamic LLM providers/models and which are active (key present)."""
    return {"providers": providers.provider_defs(), "active": providers.available_order()}


def tool_provider_create(args):
    """Add/update an LLM provider (http: base_url+key; cli: command+model)."""
    cmd = args.get("command")
    if isinstance(cmd, str):
        s = cmd.strip()
        if s.startswith("["):
            try:
                cmd = json.loads(s)
            except json.JSONDecodeError:
                cmd = [x for x in s.split("|") if x]
        elif "|" in s:
            cmd = [x for x in s.split("|") if x]
        elif s:
            cmd = [s]
    return providers.upsert_provider(
        args.get("name"), title=args.get("title"), base_url=args.get("base_url"),
        api_key_env=args.get("api_key_env"), model=args.get("model"),
        kind=args.get("kind"), command=cmd, cwd=args.get("cwd"))


def tool_provider_delete(args):
    """Delete an LLM provider from the registry."""
    return providers.delete_provider(args.get("name"))


def tool_agent_delete(args):
    """Delete an agent definition."""
    return orchestrator.delete_agent(args.get("name"))


def tool_llm_chat(args):
    """Chat ke provider LLM. Bila auto=true & tanpa provider/model, model dipilih
    otomatis berdasarkan intent pesan (routing agen).
    """
    provider = (args.get("provider") or "").strip()
    model = (args.get("model") or "").strip() or None
    agent_name = (args.get("agent") or "").strip().lower() or None
    auto = bool(args.get("auto"))
    messages = []
    if args.get("system"):
        messages.append({"role": "system", "content": str(args["system"])})
    raw = args.get("messages")
    if isinstance(raw, str) and raw.strip():
        try:
            hist = json.loads(raw)
        except json.JSONDecodeError:
            hist = None
        if isinstance(hist, list):
            for m in hist:
                if isinstance(m, dict) and m.get("role") and m.get("content") is not None:
                    messages.append({"role": str(m["role"]), "content": str(m["content"])})
    if args.get("prompt"):
        messages.append({"role": "user", "content": str(args["prompt"])})
    if not any(m["role"] != "system" for m in messages):
        raise ValueError("prompt/messages kosong")

    if auto and not agent_name and not provider and not model:
        pick = orchestrator.route_agent(args.get("prompt") or "")
        if pick:
            agent_name = pick["agent"]
            provider = pick.get("provider") or provider
            model = pick.get("model") or model
    elif agent_name:
        a = orchestrator.get_agent(agent_name)
        if a:
            provider = provider or a.get("provider") or ""
            model = model or a.get("model") or None

    if not provider:
        avail = providers.available_order()
        if not avail:
            raise ValueError("Tidak ada provider aktif. Tambah/isi provider dulu di tab Providers.")
        provider = avail[0]
    out = providers.chat(provider, messages, model=model)
    title = ""
    if agent_name:
        title = (orchestrator.get_agent(agent_name) or {}).get("title", agent_name)
    return {
        "provider": provider,
        "model": model or (providers.get_provider(provider) or {}).get("model"),
        "agent": agent_name or "",
        "title": title,
        "content": out.get("content") or "",
    }


def tool_route_agent(args):
    """Pilih agen/model otomatis untuk sebuah pesan (preview routing)."""
    return orchestrator.route_agent(args.get("message") or args.get("prompt") or "") or {}


def tool_plan_task(args):
    """Susun workflow otomatis (bagi goal jadi langkah per peran)."""
    return orchestrator.plan_workflow(args.get("task") or args.get("message") or "")


def tool_note_add(args):
    """Tambah catatan pada sebuah project (<project>/.mcp/notes/notes.md)."""
    return projects.add_note(args.get("project"), args.get("text"))


def tool_note_list(args):
    """Lihat semua catatan sebuah project."""
    return projects.list_notes(args.get("project"))


def tool_note_update(args):
    """Ubah isi catatan ke-index (urutan sama dengan note_list)."""
    return projects.update_note(args.get("project"), args.get("index"), args.get("text"))


def tool_note_delete(args):
    """Hapus catatan ke-index (urutan sama dengan note_list)."""
    return projects.delete_note(args.get("project"), args.get("index"))


def _truthy(v, default=True):
    if v is None:
        return default
    if isinstance(v, str):
        return v.strip().lower() not in ("", "false", "0", "no", "off")
    return bool(v)


def tool_doc_generate(args):
    """Buat dokumen PRD / BRD untuk sebuah project (opsional disimpan ke <project>/docs)."""
    doc_type = (args.get("type") or args.get("doc_type") or "PRD").upper()
    project = args.get("project")
    title = args.get("title")
    context = args.get("context") or ""
    save = _truthy(args.get("save", True))
    resolved = None
    if project:
        resolved = orchestrator.resolve_project(project)
        if not resolved:
            raise ValueError("project belum terdaftar: " + str(project))
    pname = (resolved or {}).get("project") if resolved else None
    system, user, title = documents.build(doc_type, project=pname, title=title, context=context)

    content, used, source = None, None, None
    try:
        avail = providers.available_order()
        if avail:
            agent = (orchestrator.get_agent("manager") or orchestrator.get_agent("architect")
                     or orchestrator.get_agent("analyst") or {})
            prov = agent.get("provider") if agent.get("provider") in avail else avail[0]
            mdl = agent.get("model") or None
            out = providers.chat(prov, [{"role": "system", "content": system},
                                        {"role": "user", "content": user}], model=mdl, timeout=240)
            content = (out.get("content") or "").strip() or None
            used = {"provider": prov, "model": mdl or (providers.get_provider(prov) or {}).get("model")}
            if content:
                source = "model"
    except Exception as e:  # noqa: BLE001
        used = {"error": str(e)}

    existing = projects.read_doc(pname, doc_type) if resolved else {"exists": False, "content": ""}
    if not content:
        # agent mungkin menulis file sendiri (lebih panjang dari template)
        if existing.get("exists") and len(existing.get("content", "")) > 1200:
            content, source = existing["content"], "file"
        else:
            content, source = documents.fallback(doc_type, project=pname, title=title,
                                                 context=context), "template"

    result = {"type": doc_type, "title": title, "project": pname, "source": source,
              "generated": source in ("model", "file"),
              "used": used, "length": len(content), "content": content}
    if save and resolved and source != "file":
        result["file"] = projects.save_doc(pname, doc_type, content)
        result["saved"] = True
    elif source == "file":
        result["file"] = existing.get("file")
        result["saved"] = False
    return result


def tool_doc_list(args):
    """Daftar dokumen yang tersimpan di <project>/docs."""
    return projects.list_docs(args.get("project"))


def tool_doc_read(args):
    """Baca dokumen PRD/BRD yang tersimpan pada sebuah project."""
    return projects.read_doc(args.get("project"), args.get("type") or args.get("doc_type"))


def tool_doc_delete(args):
    """Hapus dokumen <project>/docs/<TYPE>.md."""
    return projects.delete_doc(args.get("project"), args.get("type") or args.get("doc_type"))


def tool_doc_questions(args):
    """Checklist pertanyaan intak untuk menyusun PRD/BRD (mengacu praktik umum)."""
    return documents.checklist(args.get("type") or args.get("doc_type"))


def tool_doc_build(args):
    """Bangun PRD/BRD deterministik dari data terstruktur, lalu simpan ke docs/."""
    doc_type = (args.get("type") or args.get("doc_type") or "PRD").upper()
    project = args.get("project") or projects.get_active()
    if not project:
        raise ValueError("project wajib diisi (atau pilih project aktif dulu)")
    if not projects.project_dir(project):
        raise ValueError("project belum terdaftar: " + str(project))
    fields = args.get("fields")
    if isinstance(fields, str):
        try:
            fields = json.loads(fields)
        except json.JSONDecodeError:
            raise ValueError("fields harus berupa JSON object")
    if fields is not None and not isinstance(fields, dict):
        raise ValueError("fields harus berupa JSON object")
    out = documents.render_structured(
        doc_type, project=project, title=args.get("title"), fields=fields,
        status=args.get("status") or "Draft", version=args.get("version") or "0.1")
    out["file"] = projects.save_doc(project, doc_type, out["content"])
    out["saved"] = True
    return out


TOOLS = {
    "list_files": {
        "name": "list_files",
        "title": "List Files",
        "description": "List directory entries (file or dir) with sizes.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Directory path"},
                           "limit": {"type": "integer", "description": "Max entries (default 500, max 2000)"}},
        },
        "icons": _icons({"source": icon_data_uri("file.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_list_files,
    },
    "read_file": {
        "name": "read_file",
        "title": "Read File",
        "description": "Read text content from a file (first 100KB).",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path"}},
            "required": ["path"],
        },
        "icons": _icons({"source": icon_data_uri("file.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_read_file,
    },
    "exec_cmd": {
        "name": "exec_cmd",
        "title": "Execute Command",
        "description": "Run a shell command and capture output (30s timeout).",
        "inputSchema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
        "icons": _icons({"source": icon_data_uri("db.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_exec_cmd,
    },
    "web_fetch": {
        "name": "web_fetch",
        "title": "Web Fetch",
        "description": "Fetch a URL and return body text (max 200KB).",
        "inputSchema": {
            "type": "object",
            "properties": {"url": {"type": "string", "format": "uri"}},
            "required": ["url"],
        },
        "icons": _icons({"source": icon_data_uri("globe.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_web_fetch,
    },
    "artisan": {
        "name": "artisan",
        "title": "Laravel Artisan",
        "description": "Run php artisan inside a Laravel/ERP project (migrate, route:list, make, test...).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Artisan command, e.g. 'migrate' or 'route:list'"},
                "path": {"type": "string", "description": "Project root path"},
            },
            "required": ["command"],
        },
        "icons": _icons({"source": icon_data_uri("file.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_artisan,
    },
    "composer": {
        "name": "composer",
        "title": "Composer",
        "description": "Run composer commands in a PHP project (install, dump-autoload...).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Composer subcommand"},
                "path": {"type": "string", "description": "Project root path"},
            },
        },
        "icons": _icons({"source": icon_data_uri("file.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_composer,
    },
    "db_sqlite": {
        "name": "db_sqlite",
        "title": "SQLite Query",
        "description": "Read-only SQL (SELECT/PRAGMA) on a SQLite database file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "db": {"type": "string", "description": "Path to .sqlite file"},
                "sql": {"type": "string", "description": "SELECT / PRAGMA / EXPLAIN query"},
            },
            "required": ["db", "sql"],
        },
        "icons": _icons({"source": icon_data_uri("db.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_db_sqlite,
    },
    "csv_stats": {
        "name": "csv_stats",
        "title": "CSV Stats",
        "description": "Summarize a CSV: filter rows, group by column, sum a column. Great for ERP exports.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the .csv file"},
                "group_by": {"type": "string", "description": "Column name to group by (e.g. vendor)"},
                "sum_col": {"type": "string", "description": "Numeric column to sum (e.g. total)"},
                "filter": {"type": "string", "description": "Row filter key=value (e.g. status=approved)"},
            },
            "required": ["path"],
        },
        "icons": _icons({"source": icon_data_uri("file.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_csv_stats,
    },
    "mysql_query": {
        "name": "mysql_query",
        "title": "MySQL Query",
        "description": "Read-only SQL (SELECT/SHOW/DESCRIBE) on a MySQL server. Creds from args or MYSQL_* env.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "SELECT/SHOW/DESCRIBE/EXPLAIN query, single statement"},
                "host": {"type": "string"}, "port": {"type": "string"},
                "user": {"type": "string"}, "password": {"type": "string"},
                "database": {"type": "string"},
            },
            "required": ["sql"],
        },
        "icons": _icons({"source": icon_data_uri("db.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_mysql_query,
    },
    "scaffold_crud": {
        "name": "scaffold_crud",
        "title": "Scaffold CRUD",
        "description": "Generate Laravel files (model+controller+migration+routes snippet) for an ERP table.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table": {"type": "string", "description": "snake_case table, e.g. purchase_orders"},
                "fields": {"type": "string", "description": "Comma list name:type (string,integer,decimal,text,boolean,date,datetime,foreign_id)"},
                "path": {"type": "string", "description": "Project root where files are written"},
                "force": {"type": "boolean", "description": "Overwrite existing files"},
            },
            "required": ["table"],
        },
        "icons": _icons({"source": icon_data_uri("file.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_scaffold_crud,
    },
    "project_list": {
        "name": "project_list",
        "title": "List Projects",
        "description": "List registered projects and their per-project prompt templates.",
        "inputSchema": {"type": "object", "properties": {}},
        "icons": _icons({"source": icon_data_uri("prompt.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_project_list,
    },
    "project_prompt_list": {
        "name": "project_prompt_list",
        "title": "List Project Prompts",
        "description": "List prompt templates (name '<project>/<slug>'), optionally filter by project.",
        "inputSchema": {
            "type": "object",
            "properties": {"project": {"type": "string", "description": "Filter by project name"}},
        },
        "icons": _icons({"source": icon_data_uri("prompt.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_project_prompt_list,
    },
    "project_prompt_create": {
        "name": "project_prompt_create",
        "title": "Create Project Prompt",
        "description": "Create a per-project prompt template file under <project>/.mcp/prompts/. Use {{arg}} placeholders in body.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Registered project name"},
                "name": {"type": "string", "description": "Prompt slug, e.g. buat-migration"},
                "body": {"type": "string", "description": "Prompt text with {{arg}} placeholders"},
                "title": {"type": "string", "description": "Human title"},
                "description": {"type": "string", "description": "Short description"},
                "args": {"type": "string", "description": "Comma list of required arg names, e.g. 'table, fields'"},
            },
            "required": ["project", "name", "body"],
        },
        "icons": _icons({"source": icon_data_uri("prompt.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_project_prompt_create,
    },
    "project_register": {
        "name": "project_register",
        "title": "Register Project",
        "description": "Register a project root path so its .mcp/prompts/ folder is discovered.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Project slug, e.g. ibt-one"},
                "path": {"type": "string", "description": "Absolute path to project root"},
            },
            "required": ["name", "path"],
        },
        "icons": _icons({"source": icon_data_uri("prompt.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_project_register,
    },
    "project_create": {
        "name": "project_create",
        "title": "Create Project",
        "description": "Create a new project folder (docs/PRD.md, docs/BRD.md, .mcp/prompts/, README.md) and register it. Becomes the active project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Project slug, e.g. toko-kopi"},
                "path": {"type": "string", "description": "Optional absolute path (default: <airmcp>/<name>)"},
                "stack": {"type": "string", "description": "Optional extra scaffold: laravel | node | python"},
                "scaffold": {"type": "boolean", "description": "Buat docs/, prompt, README (default true)"},
            },
            "required": ["name"],
        },
        "icons": _icons({"source": icon_data_uri("prompt.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_project_create,
    },
    "project_select": {
        "name": "project_select",
        "title": "Select Project",
        "description": "Set the active project. agent_run/orchestrate use it by default when no project is given.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Registered project name; empty to clear"},
            },
        },
        "icons": _icons({"source": icon_data_uri("prompt.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_project_select,
    },
    "project_active": {
        "name": "project_active",
        "title": "Active Project",
        "description": "Show which project is currently active.",
        "inputSchema": {"type": "object", "properties": {}},
        "icons": _icons({"source": icon_data_uri("prompt.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_project_active,
    },
    "agent_list": {
        "name": "agent_list",
        "title": "List Agents",
        "description": "List configured AI agents (name, provider, tools) and available providers.",
        "inputSchema": {"type": "object", "properties": {}},
        "icons": _icons({"source": icon_data_uri("ai.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_agent_list,
    },
    "agent_create": {
        "name": "agent_create",
        "title": "Create Agent",
        "description": "Create/update an agent: name, provider (openai/deepseek/hermes), system prompt, tool access.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Agent slug, e.g. architect"},
                "title": {"type": "string"},
                "provider": {"type": "string", "description": "openai / deepseek / hermes / opencode-go / auto"},
                "model": {"type": "string", "description": "Model override, e.g. opencode-go/glm-5.3"},
                "system": {"type": "string", "description": "System prompt / role"},
                "tools": {"type": "boolean", "description": "Allow tool use"},
            },
            "required": ["name"],
        },
        "icons": _icons({"source": icon_data_uri("ai.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_agent_create,
    },
    "agent_run": {
        "name": "agent_run",
        "title": "Run Agent",
        "description": "Run one agent on a task. Pass project (name) or path; path is auto-resolved.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "description": "Agent name"},
                "task": {"type": "string", "description": "Instruction for the agent"},
                "project": {"type": "string", "description": "Project name (auto -> path)"},
                "path": {"type": "string", "description": "Explicit project root path"},
                "context": {"type": "string", "description": "Prior context"},
                "simulate": {"type": "boolean", "description": "Force simulation (no API call)"},
            },
            "required": ["agent", "task"],
        },
        "icons": _icons({"source": icon_data_uri("ai.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_agent_run,
    },
    "orchestrate": {
        "name": "orchestrate",
        "title": "Orchestrate Team",
        "description": "Run a team of agents on one project. mode: pipeline | debate | supervisor. Path auto-resolved from project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Goal for the team"},
                "project": {"type": "string", "description": "Project name (auto -> path)"},
                "path": {"type": "string", "description": "Explicit project root path"},
                "team": {"type": "string", "description": "Comma list of agent names, e.g. 'architect,coder,reviewer'"},
                "mode": {"type": "string", "description": "pipeline | debate | supervisor"},
                "rounds": {"type": "integer", "description": "Rounds for debate mode"},
                "simulate": {"type": "boolean", "description": "Force simulation (no API call)"},
            },
            "required": ["task"],
        },
        "icons": _icons({"source": icon_data_uri("ai.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_orchestrate,
    },
    "project_resolve": {
        "name": "project_resolve",
        "title": "Resolve Project Path",
        "description": "Auto-pick the best project + root path matching a free-text hint.",
        "inputSchema": {
            "type": "object",
            "properties": {"hint": {"type": "string", "description": "Project name or phrase"}},
            "required": ["hint"],
        },
        "icons": _icons({"source": icon_data_uri("prompt.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_project_resolve,
    },
    "provider_list": {
        "name": "provider_list",
        "title": "List Providers",
        "description": "List dynamic LLM providers/models and which are active.",
        "inputSchema": {"type": "object", "properties": {}},
        "icons": _icons({"source": icon_data_uri("ai.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_provider_list,
    },
    "provider_create": {
        "name": "provider_create",
        "title": "Create Provider",
        "description": "Add/update an LLM provider. kind=http (base_url+api_key_env) or kind=cli (command+model, e.g. 'opencode run -m provider/model').",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Provider slug, e.g. opencode-go"},
                "title": {"type": "string"},
                "kind": {"type": "string", "description": "http (default) or cli"},
                "base_url": {"type": "string", "description": "http: chat-completions endpoint URL"},
                "api_key_env": {"type": "string", "description": "http: env var holding the API key"},
                "command": {"type": "string", "description": "cli: argv prefix; JSON list or 'exe run' or 'exe|run'"},
                "cwd": {"type": "string", "description": "cli: working directory"},
                "model": {"type": "string", "description": "Default model id"},
            },
            "required": ["name"],
        },
        "icons": _icons({"source": icon_data_uri("ai.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_provider_create,
    },
    "provider_delete": {
        "name": "provider_delete",
        "title": "Delete Provider",
        "description": "Delete an LLM provider from the registry.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
        "icons": _icons({"source": icon_data_uri("ai.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_provider_delete,
    },
    "agent_delete": {
        "name": "agent_delete",
        "title": "Delete Agent",
        "description": "Delete an agent definition.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
        "icons": _icons({"source": icon_data_uri("ai.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_agent_delete,
    },
    "llm_chat": {
        "name": "llm_chat",
        "title": "LLM Chat",
        "description": "Send a chat and get the reply. auto=true lets the server pick the model by intent. Used by the dashboard Chat tab.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "User message"},
                "messages": {"type": "string", "description": "JSON list of prior {role,content}"},
                "system": {"type": "string", "description": "System prompt"},
                "auto": {"type": "boolean", "description": "Auto-pick the agent/model by intent"},
                "agent": {"type": "string", "description": "Force an agent (overrides auto)"},
                "provider": {"type": "string", "description": "Provider name (default: first active)"},
                "model": {"type": "string", "description": "Model override"},
            },
        },
        "icons": _icons({"source": icon_data_uri("ai.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_llm_chat,
    },
    "route_agent": {
        "name": "route_agent",
        "title": "Route Agent",
        "description": "Preview which agent/model would answer a message (auto-routing by intent).",
        "inputSchema": {
            "type": "object",
            "properties": {"message": {"type": "string", "description": "Message to route"}},
            "required": ["message"],
        },
        "icons": _icons({"source": icon_data_uri("ai.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_route_agent,
    },
    "plan_task": {
        "name": "plan_task",
        "title": "Plan Workflow",
        "description": "Auto-plan a goal into an ordered multi-role workflow (who does what).",
        "inputSchema": {
            "type": "object",
            "properties": {"task": {"type": "string", "description": "Goal, e.g. 'buat website ERP integration'"}},
            "required": ["task"],
        },
        "icons": _icons({"source": icon_data_uri("ai.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_plan_task,
    },
    "doc_generate": {
        "name": "doc_generate",
        "title": "Generate Doc",
        "description": "Generate a PRD or BRD for a project (saved to <project>/docs/<TYPE>.md).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Registered project name"},
                "type": {"type": "string", "description": "PRD or BRD"},
                "title": {"type": "string", "description": "Document title"},
                "context": {"type": "string", "description": "Goal/description context"},
                "save": {"type": "boolean", "description": "Save to project/docs (default true)"},
            },
            "required": ["project"],
        },
        "icons": _icons({"source": icon_data_uri("file.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_doc_generate,
    },
    "doc_list": {
        "name": "doc_list",
        "title": "List Docs",
        "description": "List saved docs in <project>/docs.",
        "inputSchema": {
            "type": "object",
            "properties": {"project": {"type": "string"}},
            "required": ["project"],
        },
        "icons": _icons({"source": icon_data_uri("file.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_doc_list,
    },
    "doc_read": {
        "name": "doc_read",
        "title": "Read Doc",
        "description": "Read a saved PRD/BRD from a project.",
        "inputSchema": {
            "type": "object",
            "properties": {"project": {"type": "string"},
                           "type": {"type": "string", "description": "PRD or BRD"}},
            "required": ["project", "type"],
        },
        "icons": _icons({"source": icon_data_uri("file.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_doc_read,
    },
    "doc_delete": {
        "name": "doc_delete",
        "title": "Delete Doc",
        "description": "Delete a stored document <project>/docs/<TYPE>.md.",
        "inputSchema": {
            "type": "object",
            "properties": {"project": {"type": "string"},
                           "type": {"type": "string", "description": "PRD / BRD / nama dokumen"}},
            "required": ["project", "type"],
        },
        "icons": _icons({"source": icon_data_uri("file.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_doc_delete,
    },
    "doc_questions": {
        "name": "doc_questions",
        "title": "Doc Intake Checklist",
        "description": "Checklist pertanyaan intak untuk menyusun PRD/BRD (mengacu praktik Atlassian/Product School/IIBA BABOK).",
        "inputSchema": {
            "type": "object",
            "properties": {"type": {"type": "string", "description": "PRD atau BRD"}},
        },
        "icons": _icons({"source": icon_data_uri("prompt.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_doc_questions,
    },
    "doc_build": {
        "name": "doc_build",
        "title": "Build PRD/BRD",
        "description": "Bangun PRD/BRD deterministik dari data terstruktur (tanpa LLM) lalu simpan ke <project>/docs/<TYPE>.md.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Nama project (default: project aktif)"},
                "type": {"type": "string", "description": "PRD atau BRD"},
                "title": {"type": "string"},
                "status": {"type": "string", "description": "mis. Draft / Review / Final"},
                "version": {"type": "string"},
                "fields": {"type": "object",
                           "description": "Data per bagian; key mengikuti checklist doc_questions "
                                          "(problem, goals, metrics, users, stories, functional, nfr, "
                                          "out_of_scope, risks, ...). Nilai teks atau list."},
            },
        },
        "icons": _icons({"source": icon_data_uri("prompt.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_doc_build,
    },
    "note_add": {
        "name": "note_add",
        "title": "Add Note",
        "description": "Append a note to a project (<project>/.mcp/notes/notes.md).",
        "inputSchema": {
            "type": "object",
            "properties": {"project": {"type": "string"}, "text": {"type": "string"}},
            "required": ["project", "text"],
        },
        "icons": _icons({"source": icon_data_uri("prompt.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_note_add,
    },
    "note_list": {
        "name": "note_list",
        "title": "List Notes",
        "description": "List a project's notes.",
        "inputSchema": {
            "type": "object",
            "properties": {"project": {"type": "string"}},
            "required": ["project"],
        },
        "icons": _icons({"source": icon_data_uri("prompt.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_note_list,
    },
    "note_update": {
        "name": "note_update",
        "title": "Update Note",
        "description": "Edit a project note by index (same order as note_list).",
        "inputSchema": {
            "type": "object",
            "properties": {"project": {"type": "string"},
                           "index": {"type": "integer", "description": "0-based, urutan note_list"},
                           "text": {"type": "string"}},
            "required": ["project", "index", "text"],
        },
        "icons": _icons({"source": icon_data_uri("prompt.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_note_update,
    },
    "note_delete": {
        "name": "note_delete",
        "title": "Delete Note",
        "description": "Delete a project note by index (same order as note_list).",
        "inputSchema": {
            "type": "object",
            "properties": {"project": {"type": "string"},
                           "index": {"type": "integer", "description": "0-based, urutan note_list"}},
            "required": ["project", "index"],
        },
        "icons": _icons({"source": icon_data_uri("prompt.svg"), "mimeType": "image/svg+xml"}),
        "handler": tool_note_delete,
    },
}


# ---------------------------------------------------------------- resources
def file_uri_to_path(uri):
    rest = uri[len("file://"):] if uri.startswith("file://") else uri
    parsed = urlparse(uri) if "#" in uri or "?" in uri else None
    if parsed is None:
        path = rest
    else:
        path = unquote(parsed.netloc + parsed.path)
    if os.name == "nt" and path.startswith("/") and len(path) > 2 and path[2] == ":":
        path = path[1:]
    return os.path.normpath(path)


def read_file_resource(uri):
    path = security_policy.ensure_allowed_path(file_uri_to_path(uri))
    if not os.path.exists(path):
        return None
    mime = mimetypes.guess_type(path)[0] or "text/plain"
    with open(path, "rb") as f:
        raw = f.read(100_000)
    if mime.startswith("text/") or mime in ("application/json", "application/xml"):
        return {"uri": uri, "mimeType": mime, "text": raw.decode("utf-8", errors="replace")}
    return {"uri": uri, "mimeType": mime, "blob": base64.b64encode(raw).decode()}


def read_info_resource(uri):
    return {
        "uri": uri,
        "mimeType": "application/json",
        "text": json.dumps({
            "server": SERVER_INFO,
            "protocolVersion": PROTOCOL_VERSION,
            "tools": [t["name"] for t in _visible_tool_defs()],
            "nPrompts": len(PROMPTS),
            "nProjectPrompts": len(projects.prompt_defs()),
        }),
    }


def read_system_resource(uri):
    import shutil
    return {
        "uri": uri,
        "mimeType": "application/json",
        "text": json.dumps({
            "platform": sys.platform,
            "python": sys.version,
            "cwd": os.getcwd(),
            "disk_free": shutil.disk_usage(os.getcwd()).free,
        }),
    }


RESOURCES = {
    "file://": {"name": "File", "description": "Read any local file via file://<path>",
                "reader": read_file_resource, "mime": "auto"},
    "airmcp://info": {"name": "Server Info", "description": "Server metadata and tool list",
                      "reader": read_info_resource, "mime": "application/json"},
    "airmcp://system": {"name": "System Info", "description": "Platform / Python / disk info",
                        "reader": read_system_resource, "mime": "application/json"},
}


# ---------------------------------------------------------------- prompts
def prompt_code_review(args):
    code = args.get("code", "")
    return {
        "description": "Review supplied code for bugs and improvements",
        "messages": [
            {"role": "user", "content": (
                "Review the following code for correctness, performance, readability, and security. "
                "List concrete findings followed by a summary verdict.\n\n```\n" + code + "\n```"
            )},
        ],
    }


def prompt_system_instructions(args):
    domain = args.get("domain", "general assistance")
    return {
        "description": "Generate a system instruction for a given domain",
        "messages": [
            {"role": "user", "content": (
                f"You are an expert assistant for: {domain}. "
                "Write concise system instructions covering tone, boundaries, "
                "escalation rules, and formatting. Output markdown only."
            )},
        ],
    }


def prompt_few_shot(args):
    examples = args.get("examples", "")
    return {
        "description": "Build a few-shot prompt from examples",
        "messages": [
            {"role": "user", "content": "Learn the pattern from these examples:\n\n" + examples},
            {"role": "assistant", "content": "Pattern learned. Send input and I will apply it."},
            {"role": "user", "content": "Now apply the same pattern to my next input."},
        ],
    }


PROMPT_ICON = {"source": icon_data_uri("prompt.svg"), "mimeType": "image/svg+xml"}

PROMPTS = {
    "code-review": {
        "name": "code-review", "title": "Code Review",
        "description": "Review code for bugs/improvements",
        "arguments": [{"name": "code", "type": "string", "description": "Code to review"}],
        "icons": _icons(PROMPT_ICON),
        "handler": prompt_code_review,
    },
    "system-instructions": {
        "name": "system-instructions", "title": "System Instructions",
        "description": "System prompt generator",
        "arguments": [{"name": "domain", "type": "string", "description": "Domain of expertise"}],
        "icons": _icons(PROMPT_ICON),
        "handler": prompt_system_instructions,
    },
    "few-shot": {
        "name": "few-shot", "title": "Few-Shot",
        "description": "Few-shot prompt builder",
        "arguments": [{"name": "examples", "type": "string", "description": "Example text"}],
        "icons": _icons(PROMPT_ICON),
        "handler": prompt_few_shot,
    },
}


# ---------------------------------------------------------------- dispatchers
CLIENT_VERSION = [None]  # mutated by initialize handler


def initialize_result(params, msg):
    """Minimal, version-adaptive initialize result.

    Echo the client's protocolVersion when provided. Extra capability keys
    (elicitation, subscriptions) are only advertised to 2026-dialect clients —
    strict older parsers reject unknown fields.
    """
    client_version = None
    if isinstance(params, dict):
        client_version = params.get("protocolVersion")
        if not client_version and isinstance(params.get("_meta"), dict):
            client_version = params["_meta"].get("io.modelcontextprotocol/protocolVersion")
    version = client_version if isinstance(client_version, str) and client_version else PROTOCOL_VERSION
    CLIENT_VERSION[0] = version
    capabilities = {
        "tools": {"listChanged": True},
        "resources": {"listChanged": True},
        "prompts": {"listChanged": True},
    }
    if version.startswith("2026"):
        capabilities["elicitation"] = {}
        capabilities["subscriptions"] = {"listChanged": True}
    return {
        "protocolVersion": version,
        "capabilities": capabilities,
        "serverInfo": SERVER_INFO,
    }


def handle_tools_call(params, msg):
    name = params.get("name")
    if not isinstance(name, str):
        raise ValueError("Tool name must be a string")
    tool = TOOLS.get(name)
    if not tool:
        raise LookupError(name)
    try:
        security_policy.ensure_tool_allowed(name)
    except PermissionError as exc:
        return {"isError": True, "content": [{"type": "text", "text": str(exc)}]}
    args = params.get("arguments", {})
    if not isinstance(args, dict):
        raise ValueError("Tool arguments must be an object")
    schema = tool.get("inputSchema", {})
    for req_field in schema.get("required", []):
        if req_field not in args:
            raise ValueError(f"Missing required argument: {req_field}")
    try:
        result = tool["handler"](args)
    except Exception as exc:
        return {"isError": True, "content": [{"type": "text", "text": str(exc)}]}
    return {
        "isError": isinstance(result, dict) and (bool(result.get("error")) or result.get("exit_code", 0) != 0),
        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)}],
        "structuredContent": result if isinstance(result, dict) else {"value": result},
    }


def handle_resources_read(params, msg):
    uri = params.get("uri")
    if not uri:
        raise ValueError("Missing uri")
    for prefix, r in RESOURCES.items():
        if uri.startswith(prefix):
            data = r["reader"](uri)
            if data is None:
                raise FileNotFoundError(f"Resource not found: {uri}")
            return {"contents": [data]}
    raise FileNotFoundError(f"No reader for scheme: {uri}")


def _all_prompt_defs():
    """Global prompts + per-project prompts (names '<project>/<slug>')."""
    out = [{k: v for k, v in p_.items() if k != "handler"} for p_ in PROMPTS.values()]
    out.extend(projects.prompt_defs())
    return out


def handle_prompts_list(params, msg):
    return {"prompts": list(dialect_items(_all_prompt_defs()))}


def handle_prompts_get(params, msg):
    name = params.get("name")
    args = params.get("arguments") or {}
    if name and "/" in name:
        rendered = projects.render(name, args)
        if rendered is not None:
            return rendered
        raise LookupError(name)
    prompt = PROMPTS.get(name)
    if not prompt:
        raise LookupError(name)
    return prompt["handler"](args)


def handle_elicitation_create(params, msg):
    eid = f"e{len(pending_elicitations) + 1}"
    pending_elicitations[eid] = params
    return {
        "elicitId": eid,
        "question": params.get("question", ""),
        "choices": params.get("choices", ["ok", "cancel"]),
        "note": "STDIO server returns choices directly; wrap with UI for interactive flow.",
    }


def handle_subscriptions_listen(params, msg):
    return {
        "accepted": params.get("notifications", []),
        "stream": "stdio-inline",
        "note": "Delivered as JSON-RPC notifications on stdout.",
    }


pending_elicitations = {}

def _strip_extras(items, keys=("icons",)):
    """Remove fields unknown to older strict schemas (2025-11-25)."""
    out = []
    for item in items:
        if not isinstance(item, dict):
            out.append(item)
            continue
        out.append({k: v for k, v in item.items() if k not in keys})
    return out


def dialect_items(items):
    """Adapt resource/prompt/tool definitions to the connected client dialect."""
    items = _strip_extras(items, ("icons",))
    ver = CLIENT_VERSION[0] or PROTOCOL_VERSION
    if ver.startswith("2025") and int(ver.split("-")[1] or 0) < 12 and not ver.startswith("2025-12"):
        # 2025-11-25 and earlier: "title" was added later — keep, it is legal;
        # nothing else to cull here for now.
        return items
    return items


HANDLERS = {
    "ping": lambda p, m: {},
    "initialize": initialize_result,
    "server/discover": initialize_result,
    "tools/list": lambda p, m: {"tools": list(dialect_items([{k: v for k, v in t.items() if k != "handler"} for t in _visible_tool_defs()]))},
    "tools/call": handle_tools_call,
    "resources/list": lambda p, m: {"resources": list(dialect_items([
        {"uri": prefix, "name": r["name"], "description": r["description"], "mimeType": r["mime"]}
        for prefix, r in RESOURCES.items()
    ]))},
    "resources/read": handle_resources_read,
    "prompts/list": handle_prompts_list,
    "prompts/get": handle_prompts_get,
    "elicitation/create": handle_elicitation_create,
    "subscriptions/listen": handle_subscriptions_listen,
}


def log(*parts):
    sys.stderr.write("[airmcp] " + " ".join(str(p) for p in parts) + "\n")
    sys.stderr.flush()
    _trace(" ".join(str(p) for p in parts))


TRACE_PATH = os.environ.get("AIRMCP_TRACE")


def _trace(text):
    if not TRACE_PATH:
        return
    try:
        with open(TRACE_PATH, "a", encoding="utf-8") as f:
            import datetime
            f.write(datetime.datetime.now().isoformat(timespec="milliseconds") + " " + text + "\n")
    except OSError:
        pass


def strip_lrulookup(name):
    return None


def main():
    log(f"server {SERVER_INFO['name']} v{SERVER_INFO['version']} ready (protocol {PROTOCOL_VERSION})")
    _trace("SERVER STARTUP pid=" + str(os.getpid()))
    while True:
        msg = read_message()
        if msg is None:
            break
        method = msg.get("method")
        req_id = msg.get("id")
        if not isinstance(method, str) or not method:
            write_message(make_error(req_id, INVALID_REQUEST, "method must be a non-empty string"))
            continue
        if method:
            _trace(f"IN  {'req' if req_id else 'idless'} {method}")
        # opencode-go sends initialize without an id (or id:null) — treat any
        # non-"notifications/" method as a request and always answer it.
        is_request = bool(method) and not method.startswith("notifications/")
        if not is_request:
            log("notification received:", method)
            continue
        handler = HANDLERS.get(method)
        try:
            if not handler:
                raise KeyError(method)
            params = msg.get("params", {})
            if not isinstance(params, dict):
                raise ValueError("params must be an object")
            result = handler(params, msg)
            write_message(make_response(req_id, result))
            _trace(f"OUT resp id={req_id} ok")
        except KeyError:
            write_message(make_error(req_id, METHOD_NOT_FOUND, f"Method not found: {method}"))
            _trace(f"OUT resp id={req_id} method-not-found")
        except LookupError as e:
            write_message(make_error(req_id, INVALID_PARAMS, f"Not found: {e}"))
            _trace(f"OUT resp id={req_id} not-found")
        except (ValueError, OSError) as e:
            write_message(make_error(req_id, INVALID_PARAMS, str(e)))
            _trace(f"OUT resp id={req_id} invalid-params")
        except Exception as e:  # noqa: BLE001
            log("internal error:", repr(e))
            write_message(make_error(req_id, INTERNAL_ERROR, f"{type(e).__name__}: {e}"))
            _trace(f"OUT resp id={req_id} internal-error")
    log("server stopped")
    _trace("SERVER EOF")


if __name__ == "__main__":
    main()
