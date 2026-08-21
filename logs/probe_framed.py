#!/usr/bin/env python3
"""Minimal length-framed MCP client to validate needle-mcp end-to-end."""
import json, os, subprocess, sys, threading

BIN = os.path.expanduser("~/.local/bin/needle-mcp")

def framed(msg: dict) -> bytes:
    b = json.dumps(msg).encode()
    return f"Content-Length: {len(b)}\r\n\r\n".encode() + b

proc = subprocess.Popen([BIN], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)

def send(m): proc.stdin.write(framed(m)); proc.stdin.flush()

def read():
    # read headers
    buf = b""
    while b"\r\n\r\n" not in buf:
        ch = proc.stdout.read(1)
        if not ch: raise SystemExit("stream closed before headers")
        buf += ch
    while b"\r\n\r\n" not in buf:
        buf += proc.stdout.read(1)
    head, _, rest = buf.partition(b"\r\n\r\n")
    cl = int(dict(l.decode().split(":",1) for l in head.split(b"\r\n") if b":" in l).get("content-length","0"))
    body = rest
    while len(body) < cl:
        body += proc.stdout.read(cl - len(body))
    return json.loads(body)

send({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"clientInfo":{"name":"probe","version":"1"}}})
print("initialize:", json.dumps(read()), flush=True)
send({"jsonrpc":"2.0","id":2,"method":"tools/list"})
tools = read()
print("tools:", [t["name"] for t in tools["result"]["tools"]], flush=True)
schema = json.dumps({"name":"order_info","schema":{"type":"object","properties":{
  "order_number":{"type":"string"},"date":{"type":"string"},
  "carrier":{"type":"string"},"tracking":{"type":"string"},"total":{"type":"string"}},
  "required":["order_number","date","carrier","tracking","total"]}})
send({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"extract","arguments":{
  "text":"Order #4421 shipped on 2026-08-18 via FedEx, tracking 7729 0200 8822, total $41.99.",
  "schema":schema}}})
print("extract:", json.dumps(read()), flush=True)
proc.terminate()
