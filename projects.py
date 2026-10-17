"""Per-project prompt templates for AirMCP.

Setiap project yang terdaftar boleh punya folder `.mcp/prompts/` berisi file
`*.md`. Tiap file otomatis menjadi satu MCP prompt dengan nama
`<project>/<nama-file>` (mis. `demo-erp/buat-migration`).

Format file (frontmatter opsional):

    ---
    title: Buat Migration ERP
    description: Generate migration Laravel untuk tabel baru
    required: table, fields
    argument: table = nama tabel (snake_case)
    argument: fields = daftar field: tipe
    ---
    Buat migration Laravel untuk tabel `{{table}}` dengan field:
    {{fields}}

Placeholder `{{nama}}` diganti dari `arguments` saat prompt dipanggil.
Registry disimpan di `projects.json` (map nama -> path root project).
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(ROOT, "projects.json")
REGISTRY_EXAMPLE_PATH = os.path.join(ROOT, "projects.example.json")
STATE_PATH = os.path.join(ROOT, "state.json")
PROMPTS_SUBDIR = os.path.join(".mcp", "prompts")
_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")

# Template prompt default untuk tiap project baru (ditulis ke .mcp/prompts/).
# Token `__PROJECT__` diganti nama project saat dibuat; `{{arg}}` diisi saat dipanggil.
DEFAULT_PROMPTS = {
    "mulai-fitur": """---
title: Mulai Fitur Baru
description: Rencanakan, implementasikan, dan uji satu fitur di project ini
required: fitur
argument: fitur = nama/deskripsi fitur yang mau dibuat
argument: kriteria = kriteria selesai (opsional)
---
Kerjakan satu fitur baru di project `__PROJECT__`.

Fitur: {{fitur}}
Kriteria selesai: {{kriteria}}

Alur kerja:
1. Rencanakan langkah dan daftar file yang akan dibuat/diubah.
2. Implementasikan kode lengkap (tanpa placeholder), ikuti konvensi project.
3. Tambahkan atau perbarui pengujian bila relevan.
4. Laporkan file yang berubah dan cara menjalankannya.
""",
    "review-kode": """---
title: Review Kode
description: Review kritis target tertentu: bug, keamanan, konvensi + verdict
required: target
argument: target = file/folder/fitur yang direview
---
Review kode di project `__PROJECT__`.

Target: {{target}}

Yang harus dilaporkan:
1. Bug / perilaku salah (sertakan path dan baris).
2. Celah keamanan dan validasi input.
3. Pelanggaran konvensi project.
4. Temuan berprioritas (kritis/tinggi/sedang) + verdict: LULUS atau REVISI.
""",
    "tambah-test": """---
title: Tambah Test
description: Susun dan jalankan pengujian untuk target tertentu
required: target
argument: target = bagian/fungsi/endpoint yang diuji
---
Susun pengujian untuk project `__PROJECT__`.

Target: {{target}}

Langkah:
1. Identifikasi skenario penting (happy path, edge case, kondisi error).
2. Tulis test lengkap lalu jalankan.
3. Laporkan apa yang diuji, hasilnya (lulus/gagal), dan sisa risiko.
""",
    "tulis-docs": """---
title: Tulis Dokumentasi
description: Buat atau perbarui dokumentasi untuk topik tertentu
required: topik
argument: topik = topik yang didokumentasikan
---
Tulis dokumentasi untuk project `__PROJECT__`.

Topik: {{topik}}

Aturan:
- Ringkas, jelas, dan langsung ke inti.
- Sertakan contoh nyata (perintah/kode) bila relevan.
- Simpan di `docs/` dan sebutkan path filenya.
""",
    "analisa-project": """---
title: Analisa Project
description: Inventarisasi struktur project, temukan masalah, beri rekomendasi
---
Analisa project `__PROJECT__`.

Yang harus dikerjakan:
1. Petakan struktur folder dan teknologi yang dipakai.
2. Temukan inkonsistensi, duplikasi, dan utang teknis.
3. Beri rekomendasi berprioritas (maksimal 5) berbasis bukti dari file nyata.
4. Tutup dengan ringkasan singkat 3 baris.
""",
}

# Jenis dokumen yang dibuat otomatis untuk project baru (lihat documents.py).
DOC_TYPES = ["PRD", "BRD"]

STACK_SCAFFOLDS = {
    "laravel": {
        "dirs": ["app/Models", "app/Http/Controllers", "database/migrations",
                 "routes", "resources/views", "public", "tests/Feature", "tests/Unit"],
        "files": {
            ".gitignore": "vendor/\nnode_modules/\npublic/storage\n.env\n.env.*\n*.log\n",
            "routes/web.php": ("<?php\n\nuse Illuminate\\Support\\Facades\\Route;\n\n"
                               "Route::get('/', fn () => 'OK');\n"),
        },
    },
    "node": {
        "dirs": ["src", "tests"],
        "files": {
            ".gitignore": "node_modules/\ndist/\n.env\n*.log\n",
            "package.json": ('{\n  "name": "__PROJECT__",\n  "version": "0.1.0",\n'
                             '  "private": true,\n  "scripts": {\n'
                             '    "start": "node src/index.js",\n'
                             '    "test": "node --test"\n  }\n}\n'),
        },
    },
    "python": {
        "dirs": ["src", "tests"],
        "files": {
            ".gitignore": "__pycache__/\n*.pyc\n.venv/\n.env\n",
            "requirements.txt": "# tambahkan dependensi di sini\n",
        },
    },
}


# ------------------------------------------------------------------ registry
def load_registry():
    for registry_path in (REGISTRY_PATH, REGISTRY_EXAMPLE_PATH):
        if not os.path.exists(registry_path):
            continue
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        registry = data.get("projects", data) if isinstance(data, dict) else {}
        if not isinstance(registry, dict):
            continue
        resolved = {}
        for name, path in registry.items():
            if not isinstance(path, str):
                continue
            resolved[name] = os.path.normpath(path if os.path.isabs(path) else os.path.join(ROOT, path))
        return resolved
    return {}


def save_registry(reg):
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump({"projects": reg}, f, indent=2, ensure_ascii=False)
        f.write("\n")


def register(name, path):
    name = (name or "").strip().lower()
    if not _NAME_RE.match(name):
        raise ValueError("nama project harus slug (huruf kecil, -, _): " + str(name))
    if not path or not os.path.isdir(path):
        raise ValueError("path project tidak ada: " + str(path))
    reg = load_registry()
    reg[name] = os.path.normpath(path)
    save_registry(reg)
    return {"project": name, "path": reg[name], "registered": True}


def project_dir(project):
    return load_registry().get((project or "").strip().lower())


def _write_new(path, content):
    """Tulis file kalau belum ada (tidak menimpa). Return True kalau dibuat."""
    if os.path.exists(path):
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def create_project(name, path=None, scaffold=True, stack=None):
    """Buat folder project baru (+ scaffold, template prompt, skeleton dokumen).

    Kalau `path` kosong, folder dibuat di dalam ROOT memakai nama project.
    `stack` opsional: laravel | node | python, untuk struktur folder awal.
    """
    name = (name or "").strip().lower()
    if not _NAME_RE.match(name):
        raise ValueError("nama project harus slug (huruf kecil, -, _): " + str(name))
    stack = (stack or "").strip().lower() or None
    if stack and stack not in STACK_SCAFFOLDS:
        raise ValueError("stack tidak dikenal: " + str(stack) + " (pilihan: " +
                         ", ".join(sorted(STACK_SCAFFOLDS)) + ")")
    reg = load_registry()
    if name in reg:
        raise ValueError(f"project '{name}' sudah terdaftar: {reg[name]}")
    target = os.path.normpath(os.path.abspath(path)) if path else os.path.join(ROOT, name)
    existed = os.path.isdir(target)
    os.makedirs(target, exist_ok=True)
    made = [] if existed else [target]
    if scaffold:
        dirs = ["docs", PROMPTS_SUBDIR]
        if stack:
            dirs += STACK_SCAFFOLDS[stack]["dirs"]
        for d in dirs:
            full = os.path.join(target, d.replace("/", os.sep))
            if not os.path.isdir(full):
                os.makedirs(full, exist_ok=True)
                made.append(full)
        if _write_new(os.path.join(target, "README.md"), _readme_body(name, stack)):
            made.append(os.path.join(target, "README.md"))
        for slug, tpl in DEFAULT_PROMPTS.items():
            fp = os.path.join(target, PROMPTS_SUBDIR, slug + ".md")
            if _write_new(fp, tpl.replace("__PROJECT__", name)):
                made.append(fp)
        for doc in DOC_TYPES:
            fp = os.path.join(target, "docs", doc + ".md")
            if not os.path.exists(fp):
                import documents
                content = documents.render_structured(
                    doc, project=name)["content"]
                if _write_new(fp, content):
                    made.append(fp)
        if stack:
            for rel, body in STACK_SCAFFOLDS[stack]["files"].items():
                fp = os.path.join(target, rel.replace("/", os.sep))
                if _write_new(fp, body.replace("__PROJECT__", name)):
                    made.append(fp)
    reg[name] = target
    save_registry(reg)
    set_active(name)
    return {"project": name, "path": target, "registered": True,
            "created_dir": not existed, "scaffold": bool(scaffold), "stack": stack,
            "prompts": sorted(DEFAULT_PROMPTS) if scaffold else [],
            "docs": list(DOC_TYPES) if scaffold else [],
            "created": made}


def _readme_body(name, stack=None):
    lines = [
        f"# {name}", "",
        "Project ini dikelola lewat AirMCP.", "",
        "## Struktur", "",
        "- `docs/` - dokumen (PRD/BRD/desain/catatan rilis)",
        "- `.mcp/prompts/` - prompt template per project; muncul di MCP `prompts/list`",
        "  sebagai `<project>/<slug>`",
        "- `.mcp/notes/` - catatan project (dibuat otomatis saat menambah note)", "",
    ]
    if stack:
        lines += [f"Stack: `{stack}`", "",
                  "Folder awal: " + ", ".join(
                      f"`{d}`" for d in STACK_SCAFFOLDS[stack]["dirs"]), ""]
    lines += ["## Prompt siap pakai", ""]
    for slug in sorted(DEFAULT_PROMPTS):
        title = _prompt_title(DEFAULT_PROMPTS[slug], slug)
        lines.append(f"- `{name}/{slug}` - {title}")
    lines += ["", "## Dokumen", ""]
    for doc in DOC_TYPES:
        lines.append(f"- `docs/{doc}.md` - skeleton {doc}")
    lines += ["", "## Mulai", "",
              "Pilih project ini sebagai project aktif, lalu minta agen mengerjakan tugasnya.",
              "Path root selalu dipakai untuk semua operasi file/tool.", ""]
    return "\n".join(lines)


def _prompt_title(text, slug):
    for raw in text.splitlines():
        line = raw.strip()
        if line.lower().startswith("title:"):
            return line.split(":", 1)[1].strip()
    return slug.replace("-", " ").title()


# ------------------------------------------------------------------ active
def _load_state():
    if not os.path.exists(STATE_PATH):
        return {}
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")


def set_active(project):
    """Tandai project aktif (dipakai default oleh agent_run/orchestrate)."""
    state = _load_state()
    if not project:
        state.pop("active_project", None)
        _save_state(state)
        return {"active_project": None, "cleared": True}
    name = str(project).strip().lower()
    if name not in load_registry():
        raise ValueError("project belum terdaftar: " + name)
    state["active_project"] = name
    _save_state(state)
    return {"active_project": name, "path": project_dir(name)}


def get_active():
    name = _load_state().get("active_project")
    if name and name in load_registry():
        return name
    return None


def prompts_dir(project):
    root = project_dir(project)
    if not root:
        return None
    return os.path.join(root, PROMPTS_SUBDIR)


# ------------------------------------------------------------------ parsing
def _parse_frontmatter(text):
    meta, args, required = {}, [], []
    lines = text.splitlines()
    body = text
    if lines and lines[0].strip() == "---":
        end = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end = i
                break
        if end is not None:
            for raw in lines[1:end]:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                key, _, val = line.partition(":")
                key, val = key.strip().lower(), val.strip()
                if key == "argument":
                    nm, _, desc = val.partition("=")
                    args.append({"name": nm.strip(), "description": desc.strip()})
                elif key == "required":
                    required = [x.strip() for x in val.split(",") if x.strip()]
                elif key in ("title", "description"):
                    meta[key] = val
            body = "\n".join(lines[end + 1:]).strip("\n")
    return meta, args, required, body


def _build_arguments(args, required):
    names = [a["name"] for a in args]
    for r in required:
        if r not in names:
            args.append({"name": r, "description": ""})
            names.append(r)
    return [
        {"name": a["name"], "description": a.get("description", ""),
         "required": a["name"] in required}
        for a in args
    ]


# ------------------------------------------------------------------ loading
def _load_project(project):
    pdir = prompts_dir(project)
    out = {}
    if not pdir or not os.path.isdir(pdir):
        return out
    for fn in sorted(os.listdir(pdir)):
        if not fn.lower().endswith(".md"):
            continue
        slug = os.path.splitext(fn)[0]
        if not _NAME_RE.match(slug):
            continue
        full = os.path.join(pdir, fn)
        try:
            with open(full, "r", encoding="utf-8") as f:
                raw = f.read()
        except OSError:
            continue
        meta, args, required, body = _parse_frontmatter(raw)
        name = f"{project}/{slug}"
        out[name] = {
            "name": name,
            "title": meta.get("title", slug.replace("-", " ").title()),
            "description": meta.get("description", ""),
            "arguments": _build_arguments(args, required),
            "path": full,
            "body": body,
        }
    return out


def load_project_prompts():
    """Semua prompt dari semua project terdaftar, key = '<project>/<slug>'."""
    out = {}
    for project in load_registry():
        out.update(_load_project(project))
    return out


def get_project_prompt(name):
    if not name or "/" not in name:
        return None
    project = name.split("/", 1)[0]
    return _load_project(project).get(name)


def prompt_defs(project=None):
    """Definisi prompt (tanpa body) untuk prompts/list."""
    if project:
        items = _load_project(project.strip().lower()).values()
    else:
        items = load_project_prompts().values()
    return [
        {"name": p["name"], "title": p["title"], "description": p["description"],
         "arguments": p["arguments"]}
        for p in items
    ]


def render(name, arguments):
    pr = get_project_prompt(name)
    if not pr:
        return None
    arguments = arguments or {}
    body = pr["body"]
    missing = []
    for a in pr["arguments"]:
        key = a["name"]
        if str(arguments.get(key, "")).strip():
            body = body.replace("{{" + key + "}}", str(arguments[key]))
        elif "{{" + key + "}}" in body:
            missing.append(key)
    if missing:
        body = ("[AirMCP] argumen belum diisi: " + ", ".join(missing) +
                ". Kirim lewat arguments.\n\n" + body)
    return {"description": pr["description"],
            "messages": [{"role": "user", "content": body}]}


# ------------------------------------------------------------------ create
def create_prompt(project, name, body, title=None, description=None, args=None):
    project = (project or "").strip().lower()
    name = (name or "").strip().lower()
    if not _NAME_RE.match(project or ""):
        raise ValueError("project tidak valid / belum terdaftar: " + str(project))
    if not project_dir(project):
        raise ValueError("project belum terdaftar. Pakai project_register dulu.")
    if not _NAME_RE.match(name or ""):
        raise ValueError("nama prompt harus slug (huruf kecil, -, _)")
    if not (body or "").strip():
        raise ValueError("body kosong")
    req = [x.strip() for x in (args or "").split(",") if x.strip()]
    pdir = prompts_dir(project)
    os.makedirs(pdir, exist_ok=True)
    full = os.path.join(pdir, name + ".md")

    lines = ["---"]
    lines.append("title: " + (title or name.replace("-", " ").title()))
    if description:
        lines.append("description: " + description)
    if req:
        lines.append("required: " + ", ".join(req))
        for r in req:
            lines.append(f"argument: {r} = ")
    lines.append("---")
    content = "\n".join(lines) + "\n\n" + body.strip() + "\n"

    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    return {"project": project, "name": name, "file": full,
            "prompt_name": f"{project}/{name}", "arguments": req,
            "created": True}


def list_projects():
    reg = load_registry()
    active = get_active()
    out = []
    for name, path in reg.items():
        loaded = _load_project(name)
        out.append({
            "project": name,
            "path": path,
            "exists": os.path.isdir(path),
            "active": name == active,
            "prompts": [p["name"] for p in loaded.values()],
        })
    return out


# ------------------------------------------------------------------ notes
def _now():
    import datetime
    return datetime.datetime.now().isoformat(timespec="seconds")


def notes_file(project):
    root = project_dir(project)
    if not root:
        raise ValueError("project belum terdaftar: " + str(project))
    return os.path.join(root, ".mcp", "notes", "notes.md")


def add_note(project, text):
    text = (text or "").strip()
    if not text:
        raise ValueError("catatan kosong")
    path = notes_file(project)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"- [{_now()}] {text}\n")
    return {"project": project, "file": path, "added": text}


def _read_notes(project):
    """Return (lines, entries). Tiap entry punya 'line' (indeks di file), 'time', 'text'."""
    path = notes_file(project)
    lines = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    entries = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s:
            continue
        if s.startswith("- ["):
            ts, _, body = s[3:].partition("] ")
            entries.append({"time": ts, "text": body, "line": i})
        else:
            entries.append({"time": "", "text": s, "line": i})
    return lines, entries


def _write_notes(project, lines):
    path = notes_file(project)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))


def list_notes(project):
    path = notes_file(project)
    _, entries = _read_notes(project)
    notes = [{"time": e["time"], "text": e["text"]} for e in entries]
    return {"project": project, "file": path, "count": len(notes), "notes": notes}


def update_note(project, index, text):
    """Ubah isi catatan ke-`index` (urutan sama dengan list_notes)."""
    text = (text or "").strip()
    if not text:
        raise ValueError("catatan kosong")
    lines, entries = _read_notes(project)
    idx = int(index)
    if idx < 0 or idx >= len(entries):
        raise ValueError("index catatan tidak valid: " + str(index))
    ent = entries[idx]
    ts = ent["time"] or _now()
    lines[ent["line"]] = f"- [{ts}] {text}"
    _write_notes(project, lines)
    return {"project": project, "index": idx, "updated": True, "time": ts, "text": text}


def delete_note(project, index):
    """Hapus catatan ke-`index` (urutan sama dengan list_notes)."""
    lines, entries = _read_notes(project)
    idx = int(index)
    if idx < 0 or idx >= len(entries):
        raise ValueError("index catatan tidak valid: " + str(index))
    ent = entries[idx]
    lines.pop(ent["line"])
    _write_notes(project, lines)
    return {"project": project, "index": idx, "deleted": True, "was": ent["text"]}


# ------------------------------------------------------------------ docs
def docs_dir(project):
    root = project_dir(project)
    if not root:
        raise ValueError("project belum terdaftar: " + str(project))
    return os.path.join(root, "docs")


def save_doc(project, doc_type, content):
    path = os.path.join(docs_dir(project), (doc_type or "DOC").upper() + ".md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def list_docs(project):
    d = docs_dir(project)
    files = []
    if os.path.isdir(d):
        files = sorted(fn for fn in os.listdir(d) if fn.lower().endswith(".md"))
    return {"project": project, "dir": d, "files": files}


def read_doc(project, doc_type):
    path = os.path.join(docs_dir(project), (doc_type or "").upper() + ".md")
    if not os.path.exists(path):
        return {"project": project, "file": path, "exists": False, "content": ""}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return {"project": project, "file": path, "exists": True, "content": f.read()}


def delete_doc(project, doc_type):
    """Hapus dokumen <project>/docs/<TYPE>.md."""
    dt = (doc_type or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", dt):
        raise ValueError("nama dokumen tidak valid: " + str(doc_type))
    path = os.path.join(docs_dir(project), dt.upper() + ".md")
    if not os.path.exists(path):
        raise ValueError("dokumen tidak ada: " + dt.upper() + ".md")
    os.remove(path)
    return {"project": project, "type": dt.upper(), "file": path, "deleted": True}
