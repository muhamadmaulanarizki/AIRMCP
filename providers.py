"""Dynamic LLM provider registry for AirMCP.

Provider/model disimpan di `providers.json`. Tiap provider: base_url (endpoint
chat-completions), nama env var API key, model default, dan header opsional.
Semua bisa diubah/ditambah lewat tool `provider_create` / `provider_delete`
atau dari dashboard. Provider yang env key-nya terisi = "aktif".
"""
import json
import os
import re
import shutil
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
PROVIDERS_PATH = os.path.join(ROOT, "providers.json")
_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")

DEFAULTS = {
    "openai": {
        "title": "OpenAI",
        "base_url": "https://api.openai.com/v1/chat/completions",
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-4o",
    },
    "deepseek": {
        "title": "DeepSeek",
        "base_url": "https://api.deepseek.com/chat/completions",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
    },
    "hermes": {
        "title": "Hermes (OpenRouter)",
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "api_key_env": "HERMES_API_KEY",
        "model": "nousresearch/hermes-3-llama-3.1-405b",
        "fallback_key_env": "OPENROUTER_API_KEY",
        "headers": {"HTTP-Referer": "https://localhost/airmcp", "X-Title": "AirMCP Solo"},
    },
    "opencode-go": {
        "title": "Opencode Go (isi base_url + key)",
        "base_url": "",
        "api_key_env": "OPENCODE_GO_API_KEY",
        "model": "deepseek-v4.1-flash",
    },
}


# ------------------------------------------------------------------ registry
def load_providers():
    reg = {}
    if os.path.exists(PROVIDERS_PATH):
        try:
            with open(PROVIDERS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            reg = data.get("providers", data) if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            reg = {}
    if not isinstance(reg, dict) or not reg:
        reg = {k: dict(v) for k, v in DEFAULTS.items()}
    return reg


def save_providers(reg):
    with open(PROVIDERS_PATH, "w", encoding="utf-8") as f:
        json.dump({"providers": reg}, f, indent=2, ensure_ascii=False)
        f.write("\n")


def get_provider(name):
    return load_providers().get((name or "").strip().lower())


def _kind(prov):
    return (prov.get("kind") or "http").strip().lower()


def _key(prov):
    for env in (prov.get("api_key_env"), prov.get("fallback_key_env")):
        if env and os.environ.get(env):
            return os.environ[env]
    return prov.get("api_key") or ""


def is_available(name):
    prov = get_provider(name)
    if not prov:
        return False
    if _kind(prov) == "cli":
        cmd = prov.get("command")
        if isinstance(cmd, str):
            cmd = [cmd]
        if not cmd:
            return False
        exe = cmd[0]
        return os.path.exists(exe) or shutil.which(exe) is not None
    if not prov.get("base_url"):
        return False
    return bool(_key(prov))


def available_order():
    return [n for n in load_providers() if is_available(n)]


def provider_defs():
    out = []
    for n, p in load_providers().items():
        cmd = p.get("command")
        out.append({
            "name": n,
            "title": p.get("title", n),
            "kind": _kind(p),
            "model": p.get("model", ""),
            "base_url": p.get("base_url", ""),
            "api_key_env": p.get("api_key_env", ""),
            "command": "|".join(cmd) if isinstance(cmd, list) else (cmd or ""),
            "cwd": p.get("cwd", ""),
            "available": is_available(n),
        })
    return out


def upsert_provider(name, title=None, base_url=None, api_key_env=None,
                    model=None, headers=None, kind=None, command=None, cwd=None):
    name = (name or "").strip().lower()
    if not name or not name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("nama provider harus slug: " + str(name))
    kind = (kind or "http").strip().lower()
    if kind == "cli":
        if not command:
            raise ValueError("provider tipe cli butuh field 'command'")
    elif not base_url:
        raise ValueError("base_url wajib (endpoint chat-completions)")
    reg = load_providers()
    cur = reg.get(name, {})
    cur["title"] = title or cur.get("title") or name.title()
    cur["kind"] = kind
    if model:
        cur["model"] = model
    if kind == "cli":
        cur["command"] = command
        if cwd:
            cur["cwd"] = cwd
    else:
        cur["base_url"] = base_url
        cur["api_key_env"] = api_key_env or cur.get("api_key_env") or (name.upper() + "_API_KEY")
    if headers:
        cur["headers"] = headers
    reg[name] = cur
    save_providers(reg)
    return {"provider": name, "saved": True, **{k: v for k, v in cur.items() if k != "headers"}}


def delete_provider(name):
    name = (name or "").strip().lower()
    reg = load_providers()
    if name not in reg:
        raise ValueError("provider tidak ditemukan: " + name)
    removed = {k: v for k, v in reg.pop(name).items() if k != "headers"}
    save_providers(reg)
    return {"provider": name, "deleted": True, "was": removed}


# ------------------------------------------------------------------ chat
def _messages_to_prompt(messages):
    parts = []
    for m in messages or []:
        role = (m.get("role") or "user").upper()
        content = m.get("content") or ""
        if role == "SYSTEM":
            parts.append("[INSTRUKSI]\n" + content)
        elif role == "TOOL":
            parts.append("[HASIL TOOL]\n" + str(content))
        else:
            parts.append(f"[{role}]\n{content}")
    return "\n\n".join(parts)


def _chat_cli(prov, messages, timeout=240, model=None):
    """Provider yang memanggil CLI (mis. `opencode run -m provider/model`)."""
    import subprocess
    cmd = prov.get("command")
    if isinstance(cmd, str):
        cmd = [cmd]
    if not cmd:
        raise RuntimeError("provider cli butuh field 'command'")
    model = model or prov.get("model")
    cwd = prov.get("cwd") or ROOT
    argv = list(cmd)
    if model:
        argv += ["-m", model]
    argv += [_messages_to_prompt(messages)]
    env = {k: v for k, v in os.environ.items() if k not in ("OPENCODE_PID",)}
    r = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout, cwd=cwd,
                       stdin=subprocess.DEVNULL, env=env)
    text = _ANSI.sub("", r.stdout or "").strip()
    if r.returncode != 0:
        err = _ANSI.sub("", (r.stderr or r.stdout or "")).strip()
        raise RuntimeError(
            f"cli provider gagal (exit {r.returncode}): {err[:300] or '(tanpa output)'}")
    if not text:
        raise RuntimeError(f"cli provider kosong (exit {r.returncode}): {(r.stderr or '')[:300]}")
    return {"content": text, "tool_calls": None}


def chat(name, messages, tools=None, timeout=None, model=None):
    prov = get_provider(name)
    if not prov:
        raise RuntimeError("provider tidak dikenal: " + str(name))
    if _kind(prov) == "cli":
        return _chat_cli(prov, messages, timeout=(timeout or prov.get("timeout", 240)), model=model)
    if not prov.get("base_url"):
        raise RuntimeError(f"provider '{name}' belum punya base_url")
    key = _key(prov)
    if not key:
        raise RuntimeError(f"API key belum diset untuk '{name}' (env {prov.get('api_key_env')})")
    payload = {"model": model or prov.get("model"), "messages": messages, "temperature": 0.7}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    headers.update(prov.get("headers") or {})
    body = json.dumps(payload).encode()
    req = urllib.request.Request(prov["base_url"], data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=(timeout or 120)) as resp:
        data = json.loads(resp.read().decode())
    msg = data["choices"][0]["message"]
    return {"content": msg.get("content"), "tool_calls": msg.get("tool_calls")}
