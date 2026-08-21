#!/usr/bin/env bash
set -u
cd /home/yugaaank/Projects/needle
# Send all three frames at once via a single heredoc to avoid shell quoting issues.
out=$(timeout 35 ~/.local/bin/needle-mcp 2>/tmp/nm_all.err <<'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"clientInfo":{"name":"probe","version":"1"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"extract","arguments":{"text":"Order #4421 shipped on 2026-08-18 via FedEx, tracking 7729 0200 8822, total $41.99.","schema":"{\"name\":\"order_info\",\"schema\":{\"type\":\"object\",\"properties\":{\"order_number\":{\"type\":\"string\"},\"date\":{\"type\":\"string\"},\"carrier\":{\"type\":\"string\"},\"tracking\":{\"type\":\"string\"},\"total\":{\"type\":\"string\"}},\"required\":[\"order_number\",\"date\",\"carrier\",\"tracking\",\"total\"]}"}}}
EOF
)
echo "exit: $?"
echo "=== id:1 ==="; echo "$out" | grep '"id":1'
echo "=== id:3 (extract) ==="; echo "$out" | grep '"id":3'
echo "=== stderr ==="; cat /tmp/nm_all.err
