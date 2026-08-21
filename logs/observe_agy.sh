#!/usr/bin/env bash
set -u
cd /tmp
: > /tmp/needle.stderr
: > /tmp/needle.stdout
# This is the MCP server entry (installed via pyproject project.scripts: needle = needle_mcp.mcp:main)
~/.local/bin/needle > /tmp/needle.stdout 2> /tmp/needle.stderr &
NEEDLE_PID=$!
sleep 3
agy --print @/tmp/probe2.md 2>/dev/null | tail -15
echo "=== SERVER STDERR (tools/list + tools/call received here) ==="
cat /tmp/needle.stderr
kill "$NEEDLE_PID" 2>/dev/null || true
