#!/usr/bin/env bash
set -u
cd /home/yugaaank/Projects/needle
echo "=== test 1: installed needle-mcp binary, raw newlines, 20s timeout ==="
timeout 20 ~/.local/bin/needle-mcp 2>/tmp/nm.err <<'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"clientInfo":{"name":"probe","version":"1"}}}

EOF
echo "test1 exit: $? ; stdout above ; stderr:"; cat /tmp/nm.err
echo
echo "=== test 2: is engine cached? ==="
ls -la ~/.cache/needle/ 2>/dev/null || echo "no cache dir"
