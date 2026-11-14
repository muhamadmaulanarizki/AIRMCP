# Local setup and verification

Source: https://github.com/muhamadmaulanarizki/AIRMCP

Requirements: Python 3.10+, Git for cloning, and `pip`. The MCP server uses STDIO. The dashboard is optional and is not needed to connect a coding agent.

## Install

If the developer has no checkout, clone the repository into a location they choose. In that checkout:

```text
python -m venv .venv
<activate the virtual environment for the current shell>
python -m pip install -r requirements.txt
```

On Windows, the interpreter is usually `<checkout>\.venv\Scripts\python.exe`; on macOS/Linux, `<checkout>/.venv/bin/python`. Existing local configuration may be kept. `.env.example`, `agents.example.json`, and `projects.example.json` are templates; do not overwrite a user's `.env`, `agents.json`, or `projects.json`.

Run a server check from the checkout using the same interpreter chosen for the MCP client:

```text
<python> client.py tools
<python> client.py call list_files path=<project-root>
```

## MCP client configuration

Use the configuration syntax supported by the user's client. This generic STDIO example needs real absolute paths and JSON-escaped backslashes on Windows:

```json
{
  "mcpServers": {
    "airmcp-solo": {
      "command": "/absolute/path/to/checkout/.venv/bin/python",
      "args": ["/absolute/path/to/checkout/mcp_server.py"]
    }
  }
}
```

For Windows, replace `command` with the absolute path to `.venv\\Scripts\\python.exe` and `args` with the absolute path to `mcp_server.py`. Restart the client after editing its MCP configuration. If it does not connect, check the Python path, script path, client logs, and whether its MCP implementation supports this server's negotiated protocol version. Do not claim support for a named client until it has been tested there.

OpenCode uses a different configuration shape. A tested Windows `opencode.json` example is:

```json
{
  "mcp": {
    "servers": {
      "airmcp-solo": {
        "type": "local",
        "command": [
          "C:/absolute/path/to/AIRMCP/.venv/Scripts/python.exe",
          "C:/absolute/path/to/AIRMCP/mcp_server.py"
        ],
        "protocol": "auto"
      }
    }
  }
}
```

OpenCode discovers this skill from `.opencode/skills/airmcp-solo/` when installed locally. See the [OpenCode MCP](https://opencode.ai/docs/mcp-servers) and [skills](https://opencode.ai/docs/skills) guides for other supported locations and configuration options.

## First useful workflow

Example user request: “Connect AirMCP to this coding agent and map the structure of my project at `<project-root>`. Suggest three next tasks based on files you actually inspect.”

Expected path: verify `tools/list`; call `project_list`; call `list_files` on the given folder; read a small number of relevant files with `read_file`; optionally call `plan_task` for an agreed goal; report findings with paths. `project_register` is optional and changes local state.

## Boundaries

AirMCP's server process has access to local developer tools. The user controls which folders and tools it may access. In production mode, `AIRMCP_ALLOWED_ROOTS` limits paths and `AIRMCP_ALLOWED_DANGEROUS_TOOLS` enables selected risky tools. Never request that the user paste API keys into chat or into a skill file. A provider is optional for file inspection and planning; running LLM agents needs a configured provider or CLI.
