"""Katalog materi integrasi NAS (read-only query di atas `catalog/sources.json`).

Data sumber hidup di `<project>/catalog/sources.json`, kontrak datanya
`<project>/catalog/sources.schema.json`. Modul ini hanya loader + validator +
filter, tanpa dependency luar (server inti stdlib-only). Dipakai oleh tool MCP
`catalog_query`, resource `nas://sources`, dan CLI langsung:

    python nas_catalog.py --protocol nfs --level basic
    python nas_catalog.py --coverage
"""
import json
import os
import re
from urllib.parse import urlparse, parse_qsl

import projects

ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROJECT = "nas-integration"
CATALOG_SUBDIR = "catalog"
SOURCES_FILE = "sources.json"
SCHEMA_FILE = "sources.schema.json"
FILTERABLE = ("id", "title", "url", "vendor", "protocol", "use_case",
              "level", "status", "hands_on", "last_seen", "notes")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def catalog_dir(project=None):
    root = projects.project_dir((project or DEFAULT_PROJECT).strip().lower())
    if not root:
        raise ValueError("project belum terdaftar: " + str(project))
    return os.path.join(root, CATALOG_SUBDIR)


def catalog_path(project=None):
    return os.path.join(catalog_dir(project), SOURCES_FILE)


def schema_path(project=None):
    return os.path.join(catalog_dir(project), SCHEMA_FILE)


def load(project=None):
    """Baca daftar sumber. Bentuk file: {"sources": [...]} atau array polos."""
    path = catalog_path(project)
    if not os.path.exists(path):
        raise ValueError("katalog belum ada: " + path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("sources", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("sources.json harus berisi array atau {sources: [...]}")
    return items


def load_schema(project=None):
    path = schema_path(project)
    if not os.path.exists(path):
        raise ValueError("skema belum ada: " + path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _check_item(item, spec, where):
    errs = []
    if not isinstance(item, dict):
        return [f"{where}: bukan objek"]
    props = spec.get("properties", {})
    for key in spec.get("required", []):
        if item.get(key) in (None, ""):
            errs.append(f"{where}: field wajib '{key}' kosong")
    for key, val in item.items():
        rule = props.get(key)
        if not rule:
            continue
        if "enum" in rule and val not in rule["enum"]:
            errs.append(f"{where}: {key}={val!r} tidak ada di enum {rule['enum']}")
        if rule.get("type") == "boolean" and not isinstance(val, bool):
            errs.append(f"{where}: {key} harus boolean")
        if rule.get("type") == "string" and not isinstance(val, str):
            errs.append(f"{where}: {key} harus string")
        if rule.get("format") == "uri":
            p = urlparse(str(val))
            if p.scheme not in ("http", "https"):
                errs.append(f"{where}: {key} bukan http(s) uri: {val}")
        if rule.get("format") == "date" and not _DATE_RE.match(str(val)):
            errs.append(f"{where}: {key} harus format YYYY-MM-DD: {val}")
        if rule.get("pattern") and not re.match(rule["pattern"], str(val)):
            errs.append(f"{where}: {key} tidak cocok pola {rule['pattern']}")
    return errs


def validate(sources, schema=None):
    """Cek list sumber terhadap skema. Return list pesan error (kosong = valid)."""
    schema = schema if schema is not None else load_schema()
    spec = schema.get("items", schema) if isinstance(schema, dict) else {}
    errs, seen = [], set()
    for i, item in enumerate(sources):
        where = item.get("id", f"#{i}") if isinstance(item, dict) else f"#{i}"
        errs.extend(_check_item(item, spec, where))
        sid = item.get("id") if isinstance(item, dict) else None
        if sid:
            if sid in seen:
                errs.append(f"{where}: id duplikat")
            seen.add(sid)
    return errs


def _match(item, key, want):
    have = item.get(key)
    if key in ("vendor", "protocol", "use_case", "level", "status", "id"):
        return have == want
    if key == "hands_on":
        return bool(have) is bool(want)
    return str(want).lower() in str(have or "").lower()


def query(project=None, **filters):
    """Filter katalog. Filter kosong/None diabaikan; `text` = pencarian bebas."""
    items = load(project)
    active = {k: v for k, v in filters.items()
              if k in FILTERABLE and v not in (None, "")}
    text = str(filters.get("text") or "").strip().lower()
    out = []
    for item in items:
        if any(not _match(item, k, v) for k, v in active.items()):
            continue
        if text and text not in json.dumps(item, ensure_ascii=False).lower():
            continue
        out.append(item)
    return out


def coverage(sources=None, project=None):
    """Ringkasan korpus + gap (kombinasi penting yang belum ada materinya)."""
    items = load(project) if sources is None else sources
    def count(key):
        out = {}
        for it in items:
            out[it.get(key)] = out.get(it.get(key), 0) + 1
        return dict(sorted(out.items(), key=lambda kv: (str(kv[0]))))
    pairs = {}
    for it in items:
        key = (it.get("protocol"), it.get("use_case"))
        pairs[key] = pairs.get(key, 0) + 1
    gaps = [f"{p}/{u}" for (p, u), n in sorted(pairs.items())
            if n == 0 or p in (None, "iscsi") and u in (None, "erp")]
    return {
        "total": len(items),
        "by_protocol": count("protocol"),
        "by_vendor": count("vendor"),
        "by_use_case": count("use_case"),
        "by_level": count("level"),
        "by_status": count("status"),
        "hands_on": sum(1 for it in items if it.get("hands_on")),
        "pairs": {f"{p}/{u}": n for (p, u), n in sorted(
            (f"{a}/{b}", n) for (a, b), n in pairs.items())},
        "gaps": gaps,
    }


def parse_uri(uri):
    """`nas://sources?protocol=nfs&level=basic` -> dict filter."""
    parsed = urlparse(uri or "")
    return {k: v for k, v in parse_qsl(parsed.query)}


def resource_payload(uri, project=None):
    """Isi resource `nas://sources` = katalog + ringkasan, sudah difilter."""
    filters = parse_uri(uri)
    items = query(project, **filters)
    cov = coverage(items)
    return {"uri": uri, "filters": filters, "count": len(items),
            "sources": items, "coverage": cov}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="query katalog materi integrasi NAS")
    ap.add_argument("--project", default=DEFAULT_PROJECT)
    for f in ("vendor", "protocol", "use_case", "level", "status", "id", "title"):
        ap.add_argument("--" + f.replace("_", "-"))
    ap.add_argument("--hands-on", action="store_true")
    ap.add_argument("--text")
    ap.add_argument("--coverage", action="store_true")
    ap.add_argument("--validate", action="store_true")
    a = ap.parse_args(argv)
    if a.validate:
        errs = validate(a.project and load(a.project) or [])
        print("\n".join(errs) if errs else f"OK: {len(load(a.project))} sumber valid")
        return 1 if errs else 0
    if a.coverage:
        print(json.dumps(coverage(project=a.project), indent=2, ensure_ascii=False))
        return 0
    filters = {k: v for k, v in vars(a).items()
               if k in FILTERABLE and v not in (None, "", False)}
    for it in query(a.project, **filters):
        print(f"{it['id']:<28} {it.get('level','?'):<13} {it.get('protocol','?'):<9} "
              f"{it.get('status','?'):<13} {it.get('title','')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())