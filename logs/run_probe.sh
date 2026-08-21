#!/usr/bin/env bash
set -u
cd /home/yugaaank/Projects/needle
timeout 40 python3 logs/probe_mcp.py > /tmp/probe.out 2> /tmp/probe.err
echo "exit: $?"
echo "=== STDOUT ==="; cat /tmp/probe.out
echo "=== needle stderr (engine download progress / errors) ==="; tail -20 /tmp/probe.err
