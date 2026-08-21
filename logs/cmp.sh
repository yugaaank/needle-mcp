#!/usr/bin/env bash
set -u
cd /home/yugaaank/Projects/needle
echo "=== HEAD mcp.py: line 57 region (S110) ==="
git show HEAD:src/needle_mcp/mcp.py | sed -n '50,60p'
echo "=== HEAD mcp.py: does it have _safe_json_loads def? ==="
git show HEAD:src/needle_mcp/mcp.py | grep -n "def _safe_json_loads"
echo "=== ruff on HEAD content as real file path ==="
git show HEAD:src/needle_mcp/mcp.py > /home/yugaaank/Projects/needle/src/needle_mcp/_orig_mcp.py
uvx ruff check src/needle_mcp/_orig_mcp.py 2>&1 | tail -3
rm -f src/needle_mcp/_orig_mcp.py
