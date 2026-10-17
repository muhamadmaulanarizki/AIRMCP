"""LLM provider bridges: OpenAI, Deepseek, Hermes (local/API).

Shared interface: chat(messages, tools=None) -> {"content": str, "tool_calls": [...]}
All bridges are optional - an LLM key not configured simply disables that bridge.
"""
import os
import json
import urllib.request

OPENROUTER_HERMES = "https://openrouter.ai/api/v1/chat/completions"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

_Model = None


def _post(url, payload, api_key, extra_headers=None):
    body = json.dumps(payload).encode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def _basic_completion(url, model, messages, api_key, tools=None, extra_headers=None):
    payload = {"model": model, "messages": messages, "temperature": 0.7}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    data = _post(url, payload, api_key, extra_headers)
    msg = data["choices"][0]["message"]
    return {
        "content": msg.get("content"),
        "tool_calls": msg.get("tool_calls"),
    }


def openai_chat(messages, tools=None):
    key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
    return _basic_completion(OPENAI_URL, model, messages, key, tools)


def deepseek_chat(messages, tools=None):
    key = os.environ.get("DEEPSEEK_API_KEY")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY not set")
    return _basic_completion(DEEPSEEK_URL, model, messages, key, tools)


def hermes_chat(messages, tools=None):
    """Hermes-3 via OpenRouter (open-weights). Set HERMES_API_KEY (OpenRouter key)."""
    key = os.environ.get("HERMES_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    model = os.environ.get("HERMES_MODEL", "nousresearch/hermes-3-llama-3.1-405b")
    if not key:
        raise RuntimeError("HERMES_API_KEY / OPENROUTER_API_KEY not set")
    headers = {"HTTP-Referer": "https://localhost/airmcp", "X-Title": "AirMCP Solo"}
    return _basic_completion(OPENROUTER_HERMES, model, messages, key, tools, headers)


BRIDGES = {
    "openai": openai_chat,
    "deepseek": deepseek_chat,
    "hermes": hermes_chat,
}

FALLBACK_ORDER = ["openai", "deepseek", "hermes"]


def route_chat(messages, tools=None, preferred=None, model=None):
    """Call the preferred provider if active, else any active provider.

    Provider registry is dynamic (providers.json); `model` overrides the
    provider's default model for this call (e.g. opencode-go/glm-5.3).
    """
    try:
        import providers
        order = providers.available_order()
        if order:
            seq = ([preferred] if preferred in order else []) + \
                  [p for p in order if p != preferred]
            errors = []
            for name in seq:
                try:
                    result = providers.chat(name, messages, tools, model=model)
                    result["provider"] = name
                    return result
                except Exception as e:  # noqa: BLE001
                    errors.append(f"{name}: {e}")
            raise RuntimeError("All providers failed: " + " | ".join(errors))
    except ImportError:
        pass

    # legacy fallback (env-based bridges)
    order = ([preferred] if preferred else []) + \
            [b for b in FALLBACK_ORDER if b != preferred]
    errors = []
    for bridge_name in order:
        bridge = BRIDGES.get(bridge_name)
        if not bridge:
            continue
        try:
            result = bridge(messages, tools)
            result["provider"] = bridge_name
            return result
        except Exception as e:  # noqa: BLE001
            errors.append(f"{bridge_name}: {e}")
    raise RuntimeError("All LLM bridges failed: " + " | ".join(errors))


def convert_mcp_tools_to_openai(tools_list):
    """Convert MCP tools/list output to OpenAI tool spec."""
    spec = []
    for t in tools_list:
        spec.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("inputSchema", {"type": "object"}),
            },
        })
    return spec
