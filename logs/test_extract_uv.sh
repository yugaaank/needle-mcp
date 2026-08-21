#!/usr/bin/env bash
set -u
cd /home/yugaaank/Projects/needle
# Use uv run (works) with raw newline framing; capture all lines, show id:3 extract result.
timeout 30 uv run needle 2>/tmp/nm3.err | tee /tmp/nm3.out <<'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"clientInfo":{"name":"probe","version":"1"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"extract","arguments":{"text":"Order #4421 shipped on 2026-08-18 via FedEx, tracking 7729 0200 8822, total $41.99.","schema":"{\"name\":\"order_info\",\"schema\":{\"type\":\"object\",\"properties\":{\"order_number\":{\"type\":\"string\"},\"date\":{\"type\":\"string\"},\"carrier\":{\"type\":\"string\"},\"tracking\":{\"type\":\"string\"},\"total\":{\"type\":\"string\"}},\"required\":[\"order_number\",\"date\",\"carrier\",\"tracking\",\"total\"]}"}}}
EOF
echo "=== exit (0=ok) ==="
echo "=== response to id:3 (extract) ==="; grep '"id":3' /tmp/nm3.out
echo "=== stderr ==="; tail -8 /tmp/nm3.err
