#!/usr/bin/env bash
set -u
cd /home/yugaaank/Projects/needle
echo "=== working tree mcp.py ==="
uvx ruff check src/needle_mcp/mcp.py 2>&1 | tail -1
echo "=== HEAD mcp.py ==="
git show HEAD:src/needle_mcp/mcp.py > /tmp/orig.py 2>/dev/null
uvx ruff check --stdin-filename mcp.py /tmp/orig.py 2>&1 | tail -1
