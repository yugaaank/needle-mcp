<div align="center">

# 🪡 Needle MCP Server

**Production-ready MCP server for local structured extraction, classification, and summarization.**

![CI](https://github.com/yugaaank/needle-mcp/actions/workflows/ci.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)

</div>

Needle MCP allows AI agents (Claude Code, etc.) to perform structured data tasks locally using [Cactus Needle](https://huggingface.co/Cactus-Compute/needle2), saving tokens and improving performance.

---

## 🚀 Features

* **Zero-shot Extraction**: Extract structured data from any text using arbitrary JSON schemas.
* **Token Pruning**: Dynamically rank and filter tools to minimize context window bloat.
* **Smart Filtering**: Chunk and search large documents locally before passing to LLMs.
* **Reliable Output**: Integrated JSON repair ensures valid parsing even when LLMs fail.
* **Performance**: SQLite-backed caching for instant re-execution of identical requests.

## 📥 Installation

```bash
uv tool install git+https://github.com/yugaaank/needle-mcp
```

## 🛠 Usage

### Claude Code

```bash
claude mcp add needle -- needle
```

### CLI

```bash
# Run the server
needle
```

## 📝 License
Distributed under the MIT License. See `LICENSE` for more information.
