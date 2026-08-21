"""Needle 2 MCP server - exposes local structured extraction and tool calling."""

import asyncio
import json
import os
import ssl
import sys
import zipfile

CACHE_DIR = os.path.expanduser("~/.cache/needle")
ENGINE_VERSION = "2.0.3"


def _ensure_engine():
    lib = os.path.join(CACHE_DIR, "libneedle.so")
    if os.path.exists(lib):
        return lib
    wheel = f"/tmp/cactus_needle-{ENGINE_VERSION}-py3-none-manylinux2014_x86_64.whl"
    if not os.path.exists(wheel):
        import urllib.request
        url = (
            f"https://huggingface.co/Cactus-Compute/needle2/"
            f"resolve/main/python/cactus_needle-{ENGINE_VERSION}-py3-none-manylinux2014_x86_64.whl"
        )
        os.makedirs(CACHE_DIR, exist_ok=True)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        urllib.request.urlretrieve(url, wheel, context=ctx)
    os.makedirs(CACHE_DIR, exist_ok=True)
    with zipfile.ZipFile(wheel) as zf:
        with open(lib, "wb") as f:
            f.write(zf.read("needle/libneedle.so"))
    return lib


lib = _ensure_engine()
import needle.agent.fetch as _fetch
_fetch.fetch_library = lambda *a, **k: lib

import needle
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ListToolsResult, CallToolResult

TOOLS = [
    Tool(
        name="extract",
        description="Extract structured data from text using a JSON schema. Returns parsed JSON.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Input text to extract data from"},
                "schema": {"type": "string", "description": "JSON schema string defining output structure"}
            },
            "required": ["text", "schema"]
        }
    ),
    Tool(
        name="call_tools",
        description="Decide which tool to call and generate arguments from natural language.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "User request in natural language"},
                "tools": {"type": "string", "description": "JSON array of tool definitions"}
            },
            "required": ["text", "tools"]
        }
    ),
    Tool(
        name="classify",
        description="Classify text into one of the given categories.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to classify"},
                "categories": {"type": "string", "description": "JSON array of category strings"}
            },
            "required": ["text", "categories"]
        }
    ),
    Tool(
        name="summarize",
        description="Summarize text into a concise summary.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to summarize"},
                "max_sentences": {"type": "integer", "description": "Max sentences", "default": 3}
            },
            "required": ["text"]
        }
    ),
]


async def handle_list_tools(ctx, params):
    return ListToolsResult(tools=TOOLS)


def _schema_to_function(name, schema):
    """Convert a JSON schema to a callable function for needle."""
    props = schema.get("properties", {})
    required = schema.get("required", [])
    doc = schema.get("description", f"Extract {name}")

    annotations = {}
    for k, v in props.items():
        t = v.get("type", "string")
        python_type = {"string": str, "number": float, "integer": int, "boolean": bool}.get(t, str)
        annotations[k] = python_type

    def fn(**kwargs):
        return kwargs

    fn.__name__ = name
    fn.__doc__ = doc
    fn.__annotations__ = annotations
    fn._needle_tool = {
        "name": name,
        "description": doc,
        "parameters": schema
    }
    return fn


async def handle_call_tool(ctx, params):
    name = params.name
    args = params.arguments

    if name == "extract":
        schema = json.loads(args["schema"])
        fn = _schema_to_function(schema.get("name", "extract"), schema)
        agent = needle.Needle(tools=[fn])
        response = agent.complete(args["text"])
        calls = response.get("function_calls") or []
        result = calls[0]["arguments"] if calls else None
        return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])

    elif name == "classify":
        cats = json.loads(args["categories"])

        def classify_fn(category: str, confidence: float):
            """Classify the input text."""
            return {"category": category, "confidence": confidence}

        classify_fn.__annotations__ = {"category": str, "confidence": float}
        # Add enum constraint via needle's schema builder
        classify_fn._needle_tool = {
            "name": "classify",
            "description": "Classify the input text",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": cats},
                    "confidence": {"type": "number"}
                },
                "required": ["category"]
            }
        }

        agent = needle.Needle(tools=[classify_fn])
        response = agent.complete(args["text"])
        calls = response.get("function_calls") or []
        result = calls[0]["arguments"] if calls else None
        return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])

    elif name == "summarize":
        max_s = args.get("max_sentences", 3)

        def summarize_fn(summary: str):
            """Summarize the input text."""
            return {"summary": summary}

        summarize_fn.__annotations__ = {"summary": str}
        summarize_fn._needle_tool = {
            "name": "summarize",
            "description": f"Summarize in {max_s} sentences or fewer",
            "parameters": {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"]
            }
        }

        agent = needle.Needle(tools=[summarize_fn])
        response = agent.complete(f"Summarize in {max_s} sentences or fewer:\n\n{args['text']}")
        calls = response.get("function_calls") or []
        result = calls[0]["arguments"] if calls else None
        return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])

    elif name == "call_tools":
        tool_list = json.loads(args["tools"])

        def make_tool(t):
            params = t.get("parameters", {}).get("properties", {})
            annotations = {}
            for k, v in params.items():
                tp = {"string": str, "number": float, "integer": int, "boolean": bool}.get(v.get("type", "string"), str)
                annotations[k] = tp

            def fn(**kwargs):
                return kwargs
            fn.__name__ = t["name"]
            fn.__doc__ = t.get("description", "")
            fn.__annotations__ = annotations
            fn._needle_tool = t
            return fn

        resolved = [make_tool(t) for t in tool_list]
        agent = needle.Needle(tools=resolved)
        response = agent.complete(args["text"])
        calls = response.get("function_calls") or []
        return CallToolResult(content=[TextContent(type="text", text=json.dumps(calls, indent=2))])

    return CallToolResult(content=[TextContent(type="text", text=f"Unknown tool: {name}")], isError=True)


server = Server(
    "needle",
    on_list_tools=handle_list_tools,
    on_call_tool=handle_call_tool,
)


def main():
    asyncio.run(main_async())


async def main_async():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    main()
