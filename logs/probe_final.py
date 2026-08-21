#!/usr/bin/env python3
"""Definitive MCP end-to-end check for the installed needle-mcp binary.
Sends Content-Length-framed JSON-RPC over stdio and prints each response."""
import json, os, subprocess, sys, time

BIN = os.path.expanduser("~/.local/bin/needle-mcp")


def frame(msg: dict) -> bytes:
    b = json.dumps(msg).encode()
    return f"Content-Length: {len(b)}\r\n\r\n".encode() + b


def send(proc, msg):
    proc.stdin.write(frame(msg))
    proc.stdin.flush()


def read_headers(proc) -> int | None:
    headers = {}
    while True:
        line = proc.stdout.readline()
        if not line:
            return None
        line = line.decode()
        if line in ("\r\n", "\n", ""):
            break
        k, _, v = line.partition(":")
        headers[k.strip().lower()] = v.strip()
    if not headers:
        return None
    return int(headers.get("content-length", 0))


def read_message(proc):
    cl = read_headers(proc)
    if cl is None:
        raise SystemExit("no response (stream closed)")
    body = proc.stdout.read(cl) if cl else b""
    return json.loads(body)


proc = subprocess.Popen([BIN], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
t0 = time.time()

send(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                       "clientInfo": {"name": "probe", "version": "1"}}})
print("initialize:", json.dumps(read_message(proc)["result"]), flush=True)

send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
names = [t["name"] for t in read_message(proc)["result"]["tools"]]
print("tools:", names, flush=True)

schema = json.dumps({"name": "order_info", "schema": {
    "type": "object",
    "properties": {"order_number": {"type": "string"}, "date": {"type": "string"},
                   "carrier": {"type": "string"}, "tracking": {"type": "string"},
                   "total": {"type": "string"}},
    "required": ["order_number", "date", "carrier", "tracking", "total"]}})

send(proc, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "extract", "arguments": {
                "text": "Order #4421 shipped on 2026-08-18 via FedEx, tracking 7729 0200 8822, total $41.99.",
                "schema": schema}}})
res = read_message(proc)
print("extract:", json.dumps(res), flush=True)
print("elapsed: %.2fs" % (time.time() - t0), flush=True)

proc.terminate()
try:
    proc.wait(timeout=5)
except Exception:
    proc.kill()
