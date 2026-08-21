#!/usr/bin/env bash
set -u
cd /home/yugaaank/Projects/needle
# Run ruff fix on my changes (mcp.py only) and see remaining
uvx ruff check --fix src/needle_mcp/mcp.py 2>&1 | tail -5
echo "=== remaining errors ==="
uvx ruff check src/needle_mcp/mcp.py 2>&1 | tail -1