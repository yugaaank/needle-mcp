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

Needle MCP exposes a local [Model Context Protocol](https://modelcontextprotocol.io) server that runs the Cactus Needle model on-device. It turns structured-extraction work — JSON extraction, classification, summarization, context pruning — into callable tools, so agents and CLIs can offload that work without a remote API.

## How it works

The server boots a single process over stdio. On startup it downloads the Needle engine wheel for the host platform (or reuses a cached copy under `~/.cache/needle`), then initializes an MCP `Server`. Every tool call is a single pass through the local model. Identical requests — same tool name and arguments — are read back from a SQLite cache at `~/.cache/needle/mcp_cache.db`, so repeats return instantly and never re-hit the model.

Inputs that exceed the context window are handled in-process: large texts are chunked and trimmed to the relevant slices before being handed to the model, which keeps latencies low and the model honest.

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


## Tools

All tools stream structured output back as JSON. Results for identical `text` + arguments are cached locally, so the second call is a cache hit.

| Tool | Purpose | Required inputs |
| --- | --- | --- |
| `extract` | Extract structured data into a JSON object matching a caller-supplied schema. | `text`, `schema` (JSON schema string) |
| `classify` | Pick one label from a fixed list of categories. | `text`, `categories` (JSON array) |
| `summarize` | Produce a short summary in N sentences or fewer (`max_sentences`, default 3). | `text` |
| `call_tools` | Decide which tool to call and generate arguments from natural language. Accepts a JSON array of tool definitions in `tools`. | `text`, `tools` |
| `route_tools` | Rank a list of tools by relevance to a query (prune the prompt you send elsewhere), returning the top `top_k` (default 3). | `text`, `tools` |
| `filter_context` | Chunk a large document and return the `max_chunks` (default 3) slices most relevant to a `query`, each `chunk_size` chars (default 500). | `text`, `query` |

## License

MIT – see the `LICENSE` file for details.