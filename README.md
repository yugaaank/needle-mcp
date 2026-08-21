# Needle MCP Server

An MCP (Model Context Protocol) server that wraps `cactus-needle` for local, zero-shot structured text extraction, classification, and summarization.

## Features

This server exposes the following tools to any compatible MCP client:

* **extract**. Extracts structured data matching a user-provided JSON schema from input text.
* **call_tools**. Generates structured tool arguments from a natural language request and a set of tool definitions.
* **classify**. Classifies text into one of several user-defined categories.
* **summarize**. Summarizes input text in a specified maximum sentence count.

## Prerequisites

* Python 3.11 or newer.
* `uv` package manager (recommended).

## Setup and installation

You can run or install the server locally in a few ways.

### Running with uv (recommended)

`uv` allows running the server directly without manual virtualenv management or package installation.

To run it locally:
```bash
uv run needle
```

To run it directly from a GitHub repository without cloning:
```bash
uvx --from git+https://github.com/<username>/<repo-name> needle
```

### Installing globally

To install the executable globally on your system:
```bash
uv tool install .
```
This installs the `needle` command into your PATH.

## AI agent configuration

### Claude Code

To add the server to your Claude Code environment, run:

```bash
claude mcp add needle uv --project /path/to/cloned/needle run needle
```

Or, if you installed the package globally as a tool:

```bash
claude mcp add needle needle
```

### Claude Desktop

Add the server to your Claude Desktop configuration file:

* **Linux**: `~/.config/Claude/claude_desktop_config.json`
* **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
* **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add the following to the `mcpServers` block:

```json
{
  "mcpServers": {
    "needle": {
      "command": "uv",
      "args": ["--project", "/path/to/cloned/needle", "run", "needle"]
    }
  }
}
```

### Opencode

If you are using Opencode, the included `opencode.json` at the root of this project already registers the server automatically:

```json
{
  "mcp": {
    "needle": {
      "type": "local",
      "command": ["uv", "run", "needle"],
      "enabled": true,
      "timeout": 30000
    }
  }
}
```

### ohmypi, pi, and antigravity-cli

Add the configuration block to your agent's config file (usually `~/.config/ohmypi/config.json` or `~/.antigravity/mcp.json`):

```json
{
  "mcpServers": {
    "needle": {
      "command": "uv",
      "args": ["--project", "/path/to/cloned/needle", "run", "needle"]
    }
  }
}
```
