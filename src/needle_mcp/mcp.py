"""Needle 2 MCP server - exposes local structured extraction and tool calling."""

import asyncio
import json
import logging
import os
import platform
import ssl
import sys
import zipfile

CACHE_DIR = os.path.expanduser("~/.cache/needle")
ENGINE_VERSION = "2.0.3"

# Set up logging to write explicitly to stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("needle-mcp")


def _get_platform_wheel_and_lib():
    sys_name = platform.system().lower()
    machine = platform.machine().lower()
    
    # Defaults
    wheel_plat = "manylinux2014_x86_64"
    lib_name = "libneedle.so"
    
    if sys_name == "darwin":
        lib_name = "libneedle.dylib"
        if "arm" in machine or "aarch64" in machine:
            wheel_plat = "macosx_11_0_arm64"
        else:
            wheel_plat = "macosx_11_0_x86_64"
    elif sys_name == "windows":
        lib_name = "libneedle.dll"
        if "arm" in machine or "aarch64" in machine:
            wheel_plat = "win_arm64"
        else:
            wheel_plat = "win_amd64"
    elif sys_name == "linux":
        is_musl = False
        try:
            import subprocess
            out = subprocess.getoutput("ldd --version")
            if "musl" in out:
                is_musl = True
        except Exception:
            pass
            
        if "arm" in machine or "aarch64" in machine:
            wheel_plat = "musllinux_1_2_aarch64" if is_musl else "manylinux2014_aarch64"
        else:
            wheel_plat = "musllinux_1_2_x86_64" if is_musl else "manylinux2014_x86_64"
            
    return wheel_plat, lib_name


def _ensure_engine():
    # If the user explicitly provided a library path, use it.
    env_lib = os.environ.get("NEEDLE_LIB_PATH")
    if env_lib and os.path.exists(env_lib):
        return env_lib

    # Detect OS and Architecture to determine the wheel and lib name
    wheel_plat, lib_name = _get_platform_wheel_and_lib()
    lib = os.path.join(CACHE_DIR, lib_name)
    if os.path.exists(lib):
        return lib

    wheel_filename = f"cactus_needle-{ENGINE_VERSION}-py3-none-{wheel_plat}.whl"
    wheel = os.path.join(CACHE_DIR, wheel_filename)
    
    if not os.path.exists(wheel):
        import urllib.request
        url = (
            f"https://huggingface.co/Cactus-Compute/needle2/"
            f"resolve/main/python/{wheel_filename}"
        )
        logger.info(f"Downloading engine wheel from {url}...")
        os.makedirs(CACHE_DIR, exist_ok=True)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        urllib.request.urlretrieve(url, wheel, context=ctx)
        logger.info("Download completed.")

    logger.info(f"Extracting {lib_name} from wheel...")
    os.makedirs(CACHE_DIR, exist_ok=True)
    with zipfile.ZipFile(wheel) as zf:
        with open(lib, "wb") as f:
            f.write(zf.read(f"needle/{lib_name}"))
    logger.info("Extraction completed.")
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

    try:
        if name == "extract":
            if "text" not in args or "schema" not in args:
                return CallToolResult(content=[TextContent(type="text", text="Missing required parameters: text and schema")], isError=True)
            try:
                schema = json.loads(args["schema"])
            except json.JSONDecodeError as e:
                return CallToolResult(content=[TextContent(type="text", text=f"Invalid JSON schema: {e}")], isError=True)

            fn = _schema_to_function(schema.get("name", "extract"), schema)
            
            # Allow custom engine configurations via environment variables
            weights = os.environ.get("NEEDLE_WEIGHTS_PATH")
            buffer_size = int(os.environ.get("NEEDLE_BUFFER_SIZE", "65536"))
            agent = needle.Needle(
                tools=[fn],
                weights=weights,
                buffer_size=buffer_size
            )
            response = agent.complete(args["text"])
            calls = response.get("function_calls") or []
            result = calls[0]["arguments"] if calls else None
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])

        elif name == "classify":
            if "text" not in args or "categories" not in args:
                return CallToolResult(content=[TextContent(type="text", text="Missing required parameters: text and categories")], isError=True)
            try:
                cats = json.loads(args["categories"])
            except json.JSONDecodeError as e:
                return CallToolResult(content=[TextContent(type="text", text=f"Invalid categories JSON: {e}")], isError=True)

            def classify_fn(category: str, confidence: float):
                """Classify the input text."""
                return {"category": category, "confidence": confidence}

            classify_fn.__annotations__ = {"category": str, "confidence": float}
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

            weights = os.environ.get("NEEDLE_WEIGHTS_PATH")
            buffer_size = int(os.environ.get("NEEDLE_BUFFER_SIZE", "65536"))
            agent = needle.Needle(
                tools=[classify_fn],
                weights=weights,
                buffer_size=buffer_size
            )
            response = agent.complete(args["text"])
            calls = response.get("function_calls") or []
            result = calls[0]["arguments"] if calls else None
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])

        elif name == "summarize":
            if "text" not in args:
                return CallToolResult(content=[TextContent(type="text", text="Missing required parameter: text")], isError=True)
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

            weights = os.environ.get("NEEDLE_WEIGHTS_PATH")
            buffer_size = int(os.environ.get("NEEDLE_BUFFER_SIZE", "65536"))
            agent = needle.Needle(
                tools=[summarize_fn],
                weights=weights,
                buffer_size=buffer_size
            )
            response = agent.complete(f"Summarize in {max_s} sentences or fewer:\n\n{args['text']}")
            calls = response.get("function_calls") or []
            result = calls[0]["arguments"] if calls else None
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])

        elif name == "call_tools":
            if "text" not in args or "tools" not in args:
                return CallToolResult(content=[TextContent(type="text", text="Missing required parameters: text and tools")], isError=True)
            try:
                tool_list = json.loads(args["tools"])
            except json.JSONDecodeError as e:
                return CallToolResult(content=[TextContent(type="text", text=f"Invalid tools JSON: {e}")], isError=True)

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
            weights = os.environ.get("NEEDLE_WEIGHTS_PATH")
            buffer_size = int(os.environ.get("NEEDLE_BUFFER_SIZE", "65536"))
            agent = needle.Needle(
                tools=resolved,
                weights=weights,
                buffer_size=buffer_size
            )
            response = agent.complete(args["text"])
            calls = response.get("function_calls") or []
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(calls, indent=2))])

        return CallToolResult(content=[TextContent(type="text", text=f"Unknown tool: {name}")], isError=True)

    except Exception as e:
        logger.error(f"Error handling tool call {name}: {e}", exc_info=True)
        return CallToolResult(content=[TextContent(type="text", text=f"Error executing tool {name}: {str(e)}")], isError=True)


server = Server(
    "needle",
    on_list_tools=handle_list_tools,
    on_call_tool=handle_call_tool,
)


def main():
    asyncio.run(main_async())


async def main_async():
    async with stdio_server() as (read_stream, write_stream):
        # Prevent any stdout corruption inside the stdio context
        old_stdout = sys.stdout
        sys.stdout = sys.stderr
        try:
            await server.run(read_stream, write_stream, server.create_initialization_options())
        finally:
            sys.stdout = old_stdout


if __name__ == "__main__":
    main()
