"""AirMCP Terminal UI - ASCII interface with icons.

Standalone demo: shows server status, tool registry, prompts,
resources, and simulated conversation flow.
Run: python ui/terminal_ui.py
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

IC = {
    "file": "\U0001F4C4",   # page
    "globe": "\U0001F310",  # globe
    "db": "\U0001F4BE",     # floppy
    "ai": "\U0001F916",     # robot
    "prompt": "\u270F\uFE0F",  # pencil
    "bell": "\U0001F514",   # bell
    "bolt": "\u26A1",
    "check": "\u2705",
    "arrow": "\u25B6",
    "box": "\U0001F5C4",
}

TOOL_ICONS = {"list_files": "file", "read_file": "file", "exec_cmd": "db", "web_fetch": "globe"}


def banner():
    print()
    print("+" + "-" * 55 + "+")
    print("|   AIR MCP SOLO   " + IC["bolt"] + "   Model Context Protocol        |")
    print("|   protocol 2026-07-28 - STDIO - all primitives       |")
    print("+" + "-" * 55 + "+")


def show_tools():
    print()
    print(f"  {IC['bolt']} Available Tools")
    print("  " + "-" * 45)
    rows = [
        ("list_files", "file", "List directory entries with sizes"),
        ("read_file", "file", "Read text content from a file"),
        ("exec_cmd", "db", "Run shell command, capture output"),
        ("web_fetch", "globe", "Fetch URL, return body text"),
    ]
    for name, ic, desc in rows:
        print(f"  [{name:12}] {IC[TOOL_ICONS.get(name, 'file')]}  {desc}")


def show_resources():
    print()
    print(f"  {IC['box']} Resources")
    print("  " + "-" * 45)
    for uri, desc in [
        ("file://<path>", "Read any local file"),
        ("airmcp://info", "Server metadata + tool list"),
        ("airmcp://system", "Platform / Python / disk info"),
    ]:
        print(f"  {IC['file']} {uri:22} {desc}")


def show_prompts():
    print()
    print(f"  {IC['prompt']} Prompts")
    print("  " + "-" * 45)
    for name, desc in [
        ("code-review", "Review code for bugs/improvements"),
        ("system-instructions", "System prompt generator"),
        ("few-shot", "Few-shot prompt builder"),
    ]:
        print(f"  {IC['prompt']} {name:22} {desc}")


def show_providers():
    print()
    print(f"  {IC['ai']} LLM Providers (fallback order)")
    print("  " + "-" * 45)
    env_checks = [
        ("openai", "OPENAI_API_KEY"),
        ("deepseek", "DEEPSEEK_API_KEY"),
        ("hermes", "HERMES_API_KEY / OPENROUTER_API_KEY"),
    ]
    for i, (name, var) in enumerate(env_checks, 1):
        status = "? setActive" if os.environ.get(var.split(" ")[0]) else "? [no key]"
        sym = IC["check"] if os.environ.get(var.split(" ")[0]) else "[ ]"
        print(f"  {i}. {name:10} {sym} {status}")


def flow():
    print()
    print(f"  {IC['bell']} Workflow")
    print("  " + "-" * 45)
    steps = [
        "Start server  : python mcp_server.py",
        "Handshake     : initialize -> capabilities exchange",
        "Discover      : tools/list, resources/list, prompts/list",
        "Route         : pick LLM (openai -> deepseek -> hermes)",
        "Execute       : tools/call -> result",
        "Context       : result feeds conversation -> repeat",
    ]
    for i, s in enumerate(steps, 1):
        print(f"  {IC['arrow']} {s}")


def main():
    banner()
    show_tools()
    show_resources()
    show_prompts()
    show_providers()
    flow()
    print()
    print("  " + "-" * 55)
    print(f"  {IC['check']} Ready. Start server: python mcp_server.py")
    print()


if __name__ == "__main__":
    main()
