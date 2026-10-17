"""Agent orchestrator for AirMCP.

Definisi agen (nama, model/provider, system prompt, akses tool) disimpan di
`agents.json`. Orchestrator menjalankan beberapa agen secara berurutan/kolaboratif
untuk mengerjakan satu project, dengan pemilihan path otomatis dari registry
project (`projects.json`).

Mode:
  - pipeline   : agen berurutan, tiap agen menyempurnakan hasil sebelumnya
  - debate     : semua agen berdiskusi beberapa ronde
  - supervisor : agen pertama jadi lead: rencana -> delegasi -> rangkum final

Tanpa API key (`.env` kosong), orchestrator otomatis masuk MODE SIMULASI:
alur tetap terlihat jelas tapi bukan output model sungguhan.
"""
import difflib
import json
import os

import projects

ROOT = os.path.dirname(os.path.abspath(__file__))
AGENTS_PATH = os.path.join(ROOT, "agents.json")
AGENTS_EXAMPLE_PATH = os.path.join(ROOT, "agents.example.json")

PROVIDER_KEYS = {
    "openai": ["OPENAI_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
    "hermes": ["HERMES_API_KEY", "OPENROUTER_API_KEY"],
}


# ------------------------------------------------------------------ agents
def load_agents():
    for path in (AGENTS_PATH, AGENTS_EXAMPLE_PATH):
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        agents = data.get("agents", data) if isinstance(data, dict) else {}
        if isinstance(agents, dict):
            return agents
    return {}


def save_agents(reg):
    with open(AGENTS_PATH, "w", encoding="utf-8") as f:
        json.dump({"agents": reg}, f, indent=2, ensure_ascii=False)
        f.write("\n")


def get_agent(name):
    return load_agents().get((name or "").strip().lower())


def agent_defs():
    return [
        {"name": n, "title": a.get("title", n), "provider": a.get("provider", "auto"),
         "model": a.get("model", ""), "system": a.get("system", ""), "tools": bool(a.get("tools"))}
        for n, a in load_agents().items()
    ]


def create_agent(name, title=None, provider=None, system=None, tools=True, model=None):
    name = (name or "").strip().lower()
    if not name or not name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("nama agen harus slug: " + str(name))
    reg = load_agents()
    cur = reg.get(name, {})
    cur.update({
        "title": title or cur.get("title") or name.title(),
        "provider": provider or cur.get("provider") or "auto",
        "model": model if model is not None else cur.get("model", ""),
        "tools": bool(tools),
        "system": system or cur.get("system") or f"Kamu agen '{name}'. Kerjakan tugas dengan teliti dan ringkas.",
    })
    reg[name] = cur
    save_agents(reg)
    return {"agent": name, **cur, "saved": True}


def delete_agent(name):
    name = (name or "").strip().lower()
    reg = load_agents()
    if name not in reg:
        raise ValueError("agen tidak ditemukan: " + name)
    removed = reg.pop(name)
    save_agents(reg)
    return {"agent": name, "deleted": True, "was": removed.get("title", name)}


# ------------------------------------------------------------------ providers
def available_providers():
    try:
        import providers
        return providers.available_order()
    except ImportError:
        return []


# ------------------------------------------------------------------ routing
ROUTE_RULES = [
    ("reviewer", ["review", "audit", "bug", "security", "celah", "periksa", "kritik",
                  "vulnerab", "refactor", "code smell", "kesalahan", "salah", "kualitas"]),
    ("tester", ["test", "uji", "qa", "skenario", "coverage", "assert", "unit",
                "verifikasi", "regresi"]),
    ("docs", ["dokumentasi", "readme", "docs", "panduan", "tulis doc", "komentar",
              "penjelasan", "jelaskan hasil"]),
    ("analyst", ["analisa", "analisis", "data", "laporan", "riset", "banding",
                 "compare", "statistik", "ringkas", "tren", "metrik"]),
    ("architect", ["arsitektur", "architecture", "desain", "design", "schema", "skema",
                   "struktur", "database", "api", "trade-off", "migrasi", "migrate",
                   "rancang", "blueprint"]),
    ("coder", ["kode", "code", "implement", "fungsi", "endpoint", "crud", "fix",
               "perbaiki", "buat fitur", "tambah", "program", "script", "refactor kan",
               "tulis kode"]),
    ("manager", ["rencana", "roadmap", "prioritas", "plan", "tugas", "breakdown",
                 "koordinasi", "goal", "strategi", "mulai dari mana", "langkah"]),
]


def route_agent(message):
    """Pilih agen/model otomatis berdasarkan isi pesan (rule-based)."""
    msg = (message or "").lower()
    reg = load_agents()
    if not reg:
        return None
    best, best_score, hits = None, 0, []
    for role, kws in ROUTE_RULES:
        if role not in reg:
            continue
        found = [kw for kw in kws if kw in msg]
        if len(found) > best_score:
            best, best_score, hits = role, len(found), found
    if not best:
        for pref in ("manager", "architect", "coder"):
            if pref in reg:
                best = pref
                break
        if not best:
            best = next(iter(reg))
    a = reg.get(best) or {}
    return {
        "agent": best,
        "title": a.get("title", best),
        "provider": a.get("provider", ""),
        "model": a.get("model", ""),
        "reason": ("kata kunci: " + ", ".join(hits)) if hits else "default",
    }


BUILD_KW = ["buat", "buatkan", "bikin", "create", "build", "kembangkan", "develop",
            "implement", "integrasi", "integration", "website", "web", "aplikasi",
            "app", "fitur", "feature", "sistem", "system", "erp", "service", "migrasi",
            "migrate", "refactor", "kerjakan"]


def plan_workflow(task):
    """Susun workflow otomatis: bagi goal jadi langkah-langkah per peran."""
    reg = load_agents()
    msg = (task or "").lower()

    def has(keys):
        return any(k in msg for k in keys)

    if has(["review", "audit", "bug", "celah", "vulnerab"]) and not has(BUILD_KW):
        defs = [("reviewer", f"Review menyeluruh untuk: {task}. Temuan berprioritas + verdict.")]
        reason = "tugas review"
    elif has(["uji", "test", "qa", "skenario"]) and not has(BUILD_KW):
        defs = [("tester", f"Susun & jalankan pengujian untuk: {task}.")]
        reason = "tugas pengujian"
    elif has(["dokumentasi", "readme", "docs", "panduan"]) and not has(BUILD_KW):
        defs = [("docs", f"Tulis dokumentasi untuk: {task}.")]
        reason = "tugas dokumentasi"
    elif has(["analisa", "analisis", "laporan", "riset", "banding"]) and not has(BUILD_KW):
        defs = [("analyst", f"Analisa & ringkas: {task}.")]
        reason = "tugas analisa"
    else:
        defs = [
            ("manager", f"Pecah goal berikut jadi rencana kerja + daftar tugas berurutan tiap peran: {task}"),
            ("architect", f"Rancang arsitektur teknis (struktur file, skema data, endpoint & integrasi) untuk: {task}. Sebutkan file konkret."),
            ("coder", f"Implementasikan bagian inti dari: {task}. Tulis kode lengkap tanpa placeholder."),
            ("coder2", f"Implementasikan bagian integrasi/pendukung dari: {task}."),
            ("tester", f"Buat & jalankan pengujian untuk memverifikasi: {task}."),
            ("reviewer", f"Review hasil implementasi: {task}. Beri temuan berprioritas + verdict."),
            ("docs", f"Tulis dokumentasi singkat untuk: {task}."),
        ]
        reason = "workflow otomatis untuk goal"

    steps = [{"agent": a, "instruction": i} for a, i in defs if a in reg]
    if not steps:
        steps = [{"agent": a, "instruction": task} for a in reg]
    return {"mode": "pipeline", "team": [s["agent"] for s in steps],
            "steps": steps, "reason": reason}


# ------------------------------------------------------------------ auto path
def _score(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def resolve_project(hint):
    """Auto-pilih project + path dari sebuah hint (nama/path/frasa)."""
    reg = projects.load_registry()
    if not hint:
        return None
    raw = str(hint).strip()
    h = raw.lower()
    if h in reg:
        return {"project": h, "path": reg[h], "match": "exact-name"}
    if os.path.isdir(raw):
        norm = os.path.normpath(os.path.abspath(raw))
        for name, path in reg.items():
            if os.path.normpath(path).lower() == norm.lower():
                return {"project": name, "path": path, "match": "exact-path"}
        return {"project": None, "path": norm, "match": "path"}
    best, best_score = None, 0.0
    for name in reg:
        s = max(_score(h, name), _score(h, name.replace("-", " ")),
                _score(h, os.path.basename(reg[name]).lower()))
        if s > best_score:
            best, best_score = name, s
    if best and best_score >= 0.4:
        return {"project": best, "path": reg[best], "match": "fuzzy",
                "score": round(best_score, 2)}
    return None


def _resolve(project, path):
    if path and os.path.isdir(path):
        if project:
            return {"project": project, "path": os.path.normpath(os.path.abspath(path))}
        return resolve_project(path)
    if project:
        return resolve_project(project)
    active = projects.get_active()
    if active:
        res = resolve_project(active)
        if res:
            return {**res, "match": "active", "active": True}
    return None


# ------------------------------------------------------------------ run one
# Batas konteks antar-agen: cegah prompt membengkak (penyebab agen timeout).
CTX_PER_TURN = 3000
CTX_MAX_CHARS = 12000


def _clip(text, limit):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + f"\n... (dipotong, sisa {len(text) - limit} karakter)"


def _append_ctx(ctx, agent_name, out):
    ctx = (ctx or "") + f"\n\n[{agent_name}]\n{_clip(out, CTX_PER_TURN)}"
    if len(ctx) > CTX_MAX_CHARS:
        ctx = "(konteks awal dipotong)\n" + ctx[-CTX_MAX_CHARS:]
    return ctx


def _sys_prompt(agent, resolved):
    sys_prompt = agent.get("system", "")
    if resolved and resolved.get("path"):
        sys_prompt += (f"\n\nProject aktif: {resolved.get('project') or '(adhoc)'}"
                       f"\nRoot path: {resolved['path']}"
                       "\nGunakan root path ini untuk semua operasi file/tool.")
    return sys_prompt


def _activation_hint(prov_name):
    """Panduan mengaktifkan provider: CLI berbeda dari HTTP (butuh API key)."""
    try:
        import providers
        prov = providers.get_provider(prov_name) or {}
        if providers._kind(prov) == "cli":
            cmd = prov.get("command")
            exe = (cmd[0] if isinstance(cmd, list) and cmd else cmd) or "(belum diisi)"
            return (f"Provider '{prov_name}' bertipe CLI dan tidak butuh API key. "
                    f"Pastikan field 'command' di providers.json menunjuk executable "
                    f"yang benar:\n  {exe}")
        env = prov.get("api_key_env") or (str(prov_name).upper() + "_API_KEY")
        return (f"Set '{env}' di .env untuk mengaktifkan provider '{prov_name}' "
                f"dan output model sungguhan.")
    except Exception:  # noqa: BLE001
        return "Aktifkan minimal satu provider (lihat providers.json) untuk output model sungguhan."


def _simulated(agent_name, agent, task, context, resolved):
    title = agent.get("title", agent_name)
    prov = agent.get("provider", "auto")
    path = (resolved or {}).get("path", "(tidak ada project)")
    t = (task or "").strip().replace("\n", " ")
    if len(t) > 200:
        t = t[:200] + "..."
    ctx_note = f"ya ({len(context)} char)" if context else "tidak"
    steps = {
        "architect": ["Inventarisasi kebutuhan", "Rancang struktur file & skema data",
                      "Urutkan langkah implementasi"],
        "coder": ["Baca file relevan via tool", "Tulis/ubah kode nyata",
                  "Simpan ke project"],
        "reviewer": ["Periksa kebenaran & keamanan", "Cek konvensi",
                     "Keluarkan verdict"],
        "tester": ["Susun kasus uji", "Jalankan via tool", "Laporkan hasil"],
    }.get(agent_name, ["Analisa tugas", "Kerjakan", "Laporkan hasil"])
    bullets = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))
    return (f"[SIMULASI \u00b7 {title}]  (provider belum aktif \u2014 ini contoh alur, "
            f"bukan output model)\n\n"
            f"Target provider : {prov}\n"
            f"Project / path  : {path}\n"
            f"Tugas           : {t}\n"
            f"Konteks diterima: {ctx_note}\n\n"
            f"Langkah yang akan dijalankan:\n{bullets}\n\n"
            f"{_activation_hint(prov)}")


def run_agent(name, task, project=None, path=None, context=None,
              tool_executor=None, tools_spec=None, max_tool_rounds=4,
              allow_simulation=None):
    agent = get_agent(name)
    if not agent:
        raise ValueError("agen tidak dikenal: " + str(name))
    resolved = _resolve(project, path)
    avail = available_providers()

    if not avail:
        if allow_simulation is False:
            raise RuntimeError("Tidak ada LLM provider. Isi API key di .env")
        sim = True
    else:
        sim = allow_simulation is True

    if sim:
        return {"agent": name, "provider": "simulation",
                "content": _simulated(name, agent, task, context, resolved),
                "tool_calls": [], "simulated": True,
                "project": (resolved or {}).get("project"),
                "path": (resolved or {}).get("path")}

    from llm_bridges.bridges import route_chat

    messages = [{"role": "system", "content": _sys_prompt(agent, resolved)}]
    if context:
        messages.append({"role": "user", "content": "Konteks sejauh ini:\n" + context})
    messages.append({"role": "user", "content": task})

    use_tools = tools_spec if (agent.get("tools") and tool_executor and tools_spec) else None
    provider, used, content = None, [], ""
    model = agent.get("model") or None
    out = {}
    for _ in range(max_tool_rounds):
        out = route_chat(messages, tools=use_tools, preferred=agent.get("provider"), model=model)
        provider = out.get("provider")
        tcs = out.get("tool_calls")
        content = out.get("content") or ""
        if not tcs:
            break
        messages.append({"role": "assistant", "content": content, "tool_calls": tcs})
        for tc in tcs:
            fname = tc["function"]["name"]
            try:
                fargs = json.loads(tc["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                fargs = {}
            try:
                res = tool_executor(fname, fargs)
                used.append({"name": fname, "args": fargs, "ok": True})
                payload = json.dumps(res, ensure_ascii=False, default=str)
            except Exception as e:  # noqa: BLE001
                used.append({"name": fname, "args": fargs, "ok": False, "error": str(e)})
                payload = json.dumps({"error": str(e)})
            messages.append({"role": "tool", "tool_call_id": tc["id"],
                             "content": payload[:8000]})
    return {"agent": name, "provider": provider, "content": content,
            "tool_calls": used, "simulated": False,
            "project": (resolved or {}).get("project"),
            "path": (resolved or {}).get("path")}


# ------------------------------------------------------------------ orchestrate
def orchestrate(task, project=None, path=None, team=None, mode="pipeline",
                rounds=2, tool_executor=None, tools_spec=None,
                allow_simulation=None, on_turn=None, on_status=None, plan=None):
    if not task or not str(task).strip():
        raise ValueError("task kosong")
    mode = (mode or "pipeline").lower()
    auto_steps = None
    if mode == "auto":
        plan = plan_workflow(task)
        auto_steps = plan.get("steps") or []
        team = [s["agent"] for s in auto_steps]
    elif plan:
        auto_steps = plan.get("steps") or []
        if auto_steps:
            team = [s["agent"] for s in auto_steps]
    if team is None:
        team = "architect,coder,reviewer"
    if isinstance(team, str):
        team = [t.strip() for t in team.split(",") if t.strip()]
    unknown = [a for a in team if not get_agent(a)]
    if unknown:
        raise ValueError("agen tidak dikenal: " + ", ".join(unknown))

    resolved = _resolve(project, path)
    rp = (resolved or {}).get("project")
    rpath = (resolved or {}).get("path")
    avail = available_providers()
    if not avail and allow_simulation is False:
        raise RuntimeError("Tidak ada LLM provider. Isi API key di .env")
    sim = (not avail) or (allow_simulation is True)
    sim_flag = True if sim else None

    transcript = []

    def turn(agent_name, instr, context):
        if on_status:
            try:
                agent = get_agent(agent_name) or {}
                on_status({"phase": "start", "agent": agent_name,
                           "title": agent.get("title", agent_name),
                           "provider": agent.get("provider", "auto")})
            except Exception:  # noqa: BLE001
                pass
        r = run_agent(agent_name, instr, project=rp, path=rpath, context=context,
                      tool_executor=tool_executor, tools_spec=tools_spec,
                      allow_simulation=sim_flag)
        entry = {
            "agent": agent_name,
            "title": (get_agent(agent_name) or {}).get("title", agent_name),
            "provider": r.get("provider"),
            "content": r.get("content", ""),
        }
        transcript.append(entry)
        if on_turn:
            try:
                on_turn(entry)
            except Exception:  # noqa: BLE001
                pass
        return r["content"]

    if auto_steps:
        ctx = ""
        for st in auto_steps:
            out = turn(st["agent"], st.get("instruction") or task, ctx)
            ctx = _append_ctx(ctx, st["agent"], out)
    elif mode == "pipeline":
        ctx = ""
        for a in team:
            out = turn(a, task, ctx)
            ctx = _append_ctx(ctx, a, out)
    elif mode == "debate":
        convo = []
        for rnd in range(1, max(1, int(rounds)) + 1):
            for a in team:
                ctx = ("Diskusi sejauh ini:\n" + "\n".join(convo)) if convo else ""
                out = turn(a, f"{task}\n\n(Ronde {rnd})", ctx)
                convo.append(f"{a}: {_clip(out, CTX_PER_TURN)}")
                while len("\n".join(convo)) > CTX_MAX_CHARS and len(convo) > 1:
                    convo.pop(0)
    elif mode == "supervisor":
        lead = team[0]
        workers = team[1:] or team[:1]
        plan = turn(lead, "Buat rencana kerja rinci untuk tugas berikut:\n" + task, "")
        results = []
        for w in workers:
            results.append(turn(w, task, "Rencana dari lead:\n" + _clip(plan, CTX_PER_TURN)))
        turn(lead, "Rangkum & finalisasi hasil tim untuk tugas berikut:\n" + task,
             _clip("\n\n".join(results), CTX_MAX_CHARS))
    else:
        raise ValueError("mode tidak dikenal: " + mode)

    return {
        "mode": mode,
        "team": team,
        "steps": [s["agent"] for s in auto_steps] if auto_steps else None,
        "project": rp,
        "path": rpath,
        "providers_available": avail,
        "simulated": sim,
        "transcript": transcript,
    }
