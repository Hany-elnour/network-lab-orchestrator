# Configuration Files

This folder contains example configuration files required to connect Claude to EVE-NG via the MCP Toolkit Gateway. Each file serves a distinct role in the integration stack.

---

## 1. `claude_desktop_config.json`

### What it does
This is the main Claude Desktop configuration file. It tells Claude Desktop which MCP servers to load at startup, how to launch them, and what environment variables (like credentials) to pass in.

### System path
| OS | Path |
|----|------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

### Notes
- If the file doesn't exist yet, create it manually at the path above.
- After editing, **restart Claude Desktop** for changes to take effect.

---

## 2. `eveng_catalog.json`

### What it does
This is the EVE-NG tool catalog file. It declares all the tools (functions) that the EVE-NG MCP server exposes, along with their names and descriptions. The MCP Toolkit Gateway reads this file to know what capabilities the EVE-NG server provides so it can surface them to Claude.

### System path
This file lives alongside your MCP server installation. A typical location:

| OS | Path |
|----|------|
| macOS / Linux | `~/.mcp/servers/eveng/eveng_catalog.json` |
| Windows | `%APPDATA%\mcp\servers\eveng\eveng_catalog.json` |

> The exact path may vary depending on how you installed the MCP Toolkit Gateway. Check your gateway's config or documentation for the expected catalog directory.

### Notes
- Each entry in the `tools` array maps to a callable function in the MCP server.
- You can add or remove tool entries here to control which tools are exposed to Claude.
- Tool names must exactly match the function names exported by the MCP server.

---

## 3. `registry.json`

### What it does
This is the MCP Toolkit Gateway registry file. It acts as a master list of all MCP servers registered with the gateway. Each entry defines a server by its ID, how to launch it, what credentials it needs, and its tool-loading behavior.

The `toolAccess` field controls when tools are loaded:
- `"onDemand"` — tools are loaded lazily when Claude first needs them (default, recommended)
- `"eager"` — tools are loaded immediately at startup and listed in the Connectors panel

### System path
| OS | Path |
|----|------|
| macOS / Linux | `~/.mcp/registry.json` |
| Windows | `%APPDATA%\mcp\registry.json` |

### Notes
- You can register multiple MCP servers in this file by adding more entries to the `servers` array.
- The `id` field must be unique across all registered servers.
- `"onDemand"` tool access is why EVE-NG tools don't appear pre-listed in the Claude Connectors UI — they load automatically when you make a request.

---

## Quick Reference

| File | Purpose | Edited by |
|------|---------|-----------|
| `claude_desktop_config.json` | Tells Claude Desktop which MCP servers to run | User |
| `eveng_catalog.json` | Declares EVE-NG tools to the MCP Gateway | User / Server dev |
| `registry.json` | Master registry of all MCP servers in the gateway | User |

---
