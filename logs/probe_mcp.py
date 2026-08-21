#!/usr/bin/env python3
"""Tiny MCP stdio client: initialize, list tools, run extract. Validates the
installed needle-mcp binary actually speaks MCP and returns structured JSON."""
import json, subprocess, sys, time

CMD = ["~/.local/bin/needle-mcp"]
# expand ~
import os
CMD[0] = os.path.expanduser(CMD[0])

def send(proc, msg):
    data = json.dumps(msg).encode()
    frame = f"Content-Length: {len(data)}\r\n\r\n".encode() + data
    proc.stdin.write(frame)
    proc.stdin.flush()

def read_message(proc):
    headers = {}
    while True:
        line = proc.stdout.readline()
        if not line:
            raise EOFError("stream closed")
        if line == b"\r\n" or line == b"\n":
            break
        k, _, v = line.decode().partition(":")
        headers[k.strip().lower()] = v.strip()
    n = int(headers["content-length"])
    body = proc.stdout.read(n)
    return json.loads(body)

proc = subprocess.Popen(CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL, text=False)

send(proc, {"jsonrpc":"2.0","id":1,"method":"initialize",
            "params":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"clientInfo":{"name":"probe","version":"1"}}})
send(proc, {"jsonrpc":"2.0","id":2,"method":"initialized"})
send(proc, {"jsonrpc":"2.0","id":3,"method":"tools/list"})
print("tools/list:", json.dumps(read_message(proc)), flush=True)

schema = json.dumps({"name":"order_info","schema":{"type":"object","properties":{
  "order_number":{"type":"string"},"date":{"type":"string"},
  "carrier":{"type":"string"},"tracking":{"type":"string"},"total":{"type":"string"}},
  "required":["order_number","date","carrier","tracking","total"]}})
send(proc, {"jsonrpc":"2.0","id":4,"method":"tools/call",
            "params":{"name":"extract","arguments":{
              "text":"Order #4421 shipped on 2026-08-18 via FedEx, tracking 7729 0200 8822, total $41.99.",
              "schema":schema}}})
r = read_message(proc)
print("extract result:", json.dumps(r), flush=True)
proc.terminate()
