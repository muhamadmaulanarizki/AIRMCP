---
name: airmcp-solo
description: Use when a developer asks to install AirMCP Solo, connect its local MCP server to a coding agent, inspect a project with AirMCP tools, or plan a task with AirMCP agents. Requires a local AirMCP checkout and Python 3.10+.
---

# AirMCP Solo

AirMCP Solo is a local Model Context Protocol server. Use this skill to help a developer connect it to an MCP client and complete a project workflow. The server runs on the developer's machine; this skill does not contain or host the server.

## Connect

1. Find an existing AirMCP Solo checkout and a Python 3.10+ interpreter. If either is missing, follow [setup](references/setup.md). Explain the repository source and installation steps before running them.
2. Configure the user's MCP client to launch the checkout's `mcp_server.py` over STDIO with an **absolute** script path. Prefer the checkout's virtual-environment Python if dependencies were installed there. Use the client's current MCP configuration format; the generic JSON example in [setup](references/setup.md) is only a starting point.
3. Restart or reconnect the client. Confirm that `airmcp-solo` responds and that `tools/list` includes `project_list`, `list_files`, and `read_file`. If the client cannot expose MCP tools, use `python client.py tools` from the checkout to distinguish a server problem from client configuration.

## Work with a project

- Ask for the project folder if the target is unclear. Call `project_list` first. Register an existing project with `project_register` only when the user wants it added; this persists a local registry entry.
- For an initial inspection, use `list_files` on the project root, then `read_file` for selected text files. Use `project_resolve` if the user supplied a project name or hint. Summarize observed files and cite paths; do not claim to have inspected files you did not read.
- For a planning request, call `plan_task` with the user's goal. Treat its output as a proposed workflow; check it against the actual project before recommending changes.
- Use `agent_list` and `provider_list` before `agent_run` or `orchestrate`. A real LLM run needs a working provider or authenticated CLI. `simulate=true` is a dry run and must be described as such. Do not present simulated output as completed implementation.
- Calls that execute commands, change files or project state, access the network, or spend provider credits need to match the user's request. In production mode some tools are disabled until explicitly allowed by the local operator. Do not bypass those controls.

## Report

State whether the MCP connection worked, which tools and files were actually used, what changed, and what remains unverified. For setup issues, include the failed step and exact error without exposing secrets.
