# Agensi listing draft: AirMCP Solo

Status: draft for the owner's review. Proposed price: free. Package: `skills/airmcp-solo/`.

The upload archive is `dist/airmcp-solo.zip`. Rebuild it after changing the skill: from the repository root in PowerShell, run `Compress-Archive -LiteralPath skills\airmcp-solo -DestinationPath dist\airmcp-solo.zip -Force`. The archive must contain one top-level `airmcp-solo/` folder.

## Listing copy

**Title:** AirMCP Solo — Local MCP Setup and Project Workflow

**Short description:** Connect the open-source AirMCP Solo server to a coding agent, verify its tools, and inspect a local project through a repeatable MCP workflow.

**Who it is for:** Developers who already use an MCP-capable coding agent and want local project tools and optional multi-agent planning.

**What it does:** Guides the agent through installation or an existing checkout, STDIO MCP configuration, connection checks, project discovery, file inspection, and task planning. It distinguishes simulated agent runs from real provider-backed runs.

**Requirements:** Python 3.10+, a local AirMCP Solo checkout, and an MCP-capable client. Git and `pip` are needed for a fresh installation. External LLM credentials are only needed for provider-backed agent runs.

**Limitations:** The skill does not include the AirMCP server, provision a hosted service, or guarantee compatibility with every client. The dashboard is optional. Agent orchestration requires a configured provider or authenticated CLI for real model output.

**Suggested tags:** MCP, developer tools, local tools, project workflow, coding agents.

**Repository:** https://github.com/muhamadmaulanarizki/AIRMCP

## Before submitting

- Confirm the requested marketplace fields and terms with the owner. The repository now uses the MIT License.
- Codex CLI and OpenCode both loaded the skill and successfully called AirMCP MCP tools on Windows. The independent [MCP Inspector CLI](https://github.com/modelcontextprotocol/inspector/blob/main/clients/cli/README.md) also completed `tools/list`, `project_list`, and `list_files` against the STDIO server. Do not claim other agent clients have been tested. The installed VS Code agent extension could not be used for this check because its agent process was reporting repeated crashes.
- Run the repository's MCP integration tests and inspect the ZIP contents for secrets, temporary files, or machine-specific paths.
- Use the free listing first. A paid offering needs distinct value and confirmed payout and affiliate terms.
- Confirm the affiliate terms mentioned in Joeri's email in writing; the listing copy makes no affiliate or earnings promise.
