# Needle MCP Server

Production-ready MCP server for local structured extraction, classification, and summarization.

[CI](https://github.com/yugaaank/needle-mcp/actions/workflows/ci.yml) [License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)

Needle MCP lets software work with structured data on your machine. It uses the Cactus Needle model, so you keep data local and get faster responses.

---

## Features

- Extract JSON-structured data from any text without writing a prompt.
- Automatically drops unnecessary context to stay inside the model context window.
- Chunk and search large documents locally before sending them to a large language model.
- A JSON repair step guarantees parsable results.
- SQLite cache returns identical requests instantly.

## Installation

```bash
uv tool install git+https://github.com/yugaaank/needle-mcp
```

## Usage

### Claude Code

```bash
claude mcp add needle -- needle
```

### Cursor

```bash
cursor mcp add needle -- needle
```

### Claude Desktop

```bash
claude mcp add needle -- /path/to/needle
```


### Antigravity CLI

```bash
agy mcp add needle -- needle
```

### OpenCode

Add the server to your `opencode.json` under the `mcp` key:

```json
{
  "mcp": {
    "needle": {
      "type": "local",
      "command": ["needle"],
      "enabled": true,
      "timeout": 30000
    }
  }
}
```

### Oh My Pi (OMP)

Add the server to an OMP-native MCP config file:

- Project-scoped: `.omp/mcp.json`
- User-wide: `~/.omp/agent/mcp.json`

```json
{
  "$schema": "https://raw.githubusercontent.com/can1357/oh-my-pi/main/packages/coding-agent/src/config/mcp-schema.json",
  "mcpServers": {
    "needle": {
      "command": "needle"
    }
  }
}
```

Or use the interactive wizard in a running OMP session, then reload:

```bash
/mcp add
/mcp reload
```

### CLI

```bash
needle
```

## License

MIT – see the `LICENSE` file for details.