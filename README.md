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

### CLI

```bash
needle
```

## License

MIT – see the `LICENSE` file for details.