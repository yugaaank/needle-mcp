"""Needle 2 MCP server - exposes local structured extraction and tool calling."""

import asyncio
import json
import logging
import os
import platform
import ssl
import sys
import zipfile
import re

from needle_mcp.cache import get_cached_response, set_cached_response

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

async def handle_list_tools(ctx: object, params: object) -> ListToolsResult:
    return ListToolsResult(tools=TOOLS)

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
    Tool(
        name="route_tools",
        description="Rank and filter a list of tools to find the most relevant ones for a query. Use this to prune tools before sending them to the LLM system prompt.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "User intent or query text"},
                "tools": {"type": "string", "description": "JSON array of tool definitions"},
                "top_k": {"type": "integer", "description": "Max number of tools to return", "default": 3}
            },
            "required": ["text", "tools"]
        }
    ),
    Tool(
        name="filter_context",
        description="Chunk a large text document and retrieve only the chunks relevant to a query. Use this to prune large context before sending to the LLM.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Large input document text"},
                "query": {"type": "string", "description": "Search query or keywords"},
                "max_chunks": {"type": "integer", "description": "Max number of chunks to return", "default": 3},
                "chunk_size": {"type": "integer", "description": "Character size of each chunk", "default": 500}
            },
            "required": ["text", "query"]
        }
    ),
]
async def handle_list_tools(ctx: object, params: object) -> ListToolsResult:
    return ListToolsResult(tools=TOOLS)

async def handle_call_tool(ctx: object, params: object) -> CallToolResult:
    name = params.name
    args = params.arguments

    # Cache Lookup
    cache_key = {"tool": name, "arguments": args}
    cached_val = get_cached_response(cache_key)
    if cached_val is not None:
        logger.info(f"Cache hit for tool {name}")
        return CallToolResult(content=[TextContent(type="text", text=cached_val)])

    try:
        if name == "extract":
            if "text" not in args or "schema" not in args:
                return CallToolResult(content=[TextContent(type="text", text="Missing required parameters: text and schema")], isError=True)
            try:
                schema = _safe_json_loads(args["schema"])
            except Exception as e:
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
            result_str = json.dumps(result, indent=2)
            
            # Save cache
            set_cached_response(cache_key, result_str)
            return CallToolResult(content=[TextContent(type="text", text=result_str)])

        elif name == "classify":
            if "text" not in args or "categories" not in args:
                return CallToolResult(content=[TextContent(type="text", text="Missing required parameters: text and categories")], isError=True)
            try:
                cats = _safe_json_loads(args["categories"])
            except Exception as e:
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
            result_str = json.dumps(result, indent=2)
            
            # Save cache
            set_cached_response(cache_key, result_str)
            return CallToolResult(content=[TextContent(type="text", text=result_str)])

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
            result_str = json.dumps(result, indent=2)
            
            # Save cache
            set_cached_response(cache_key, result_str)
            return CallToolResult(content=[TextContent(type="text", text=result_str)])

        elif name == "call_tools":
            if "text" not in args or "tools" not in args:
                return CallToolResult(content=[TextContent(type="text", text="Missing required parameters: text and tools")], isError=True)
            try:
                tool_list = _safe_json_loads(args["tools"])
            except Exception as e:
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
            result_str = json.dumps(calls, indent=2)
            
            # Save cache
            set_cached_response(cache_key, result_str)
            return CallToolResult(content=[TextContent(type="text", text=result_str)])

        elif name == "route_tools":
            if "text" not in args or "tools" not in args:
                return CallToolResult(content=[TextContent(type="text", text="Missing required parameters: text and tools")], isError=True)
            try:
                tool_list = _safe_json_loads(args["tools"])
            except Exception as e:
                return CallToolResult(content=[TextContent(type="text", text=f"Invalid tools JSON: {e}")], isError=True)

            top_k = args.get("top_k", 3)
            
            # Simple, fast keyword matching
            def tokenize(t):
                return set(re.findall(r'\w+', t.lower()))
                
            query_tokens = tokenize(args["text"])
            if not query_tokens:
                result_str = json.dumps(tool_list[:top_k], indent=2)
                set_cached_response(cache_key, result_str)
                return CallToolResult(content=[TextContent(type="text", text=result_str)])
                
            scored_tools = []
            for t in tool_list:
                t_name = t.get("name", "")
                t_desc = t.get("description", "")
                content = f"{t_name} {t_desc}"
                props = t.get("parameters", {}).get("properties", {})
                for pk, pv in props.items():
                    content += f" {pk} {pv.get('description', '')} {pv.get('type', '')}"
                    
                tool_tokens = tokenize(content)
                intersection = query_tokens.intersection(tool_tokens)
                score = len(intersection) / len(query_tokens) if query_tokens else 0.0
                
                name_tokens = tokenize(t_name)
                if query_tokens.intersection(name_tokens):
                    score += 0.5
                    
                scored_tools.append((score, t))
                
            scored_tools.sort(key=lambda x: x[0], reverse=True)
            routed = [st[1] for st in scored_tools[:top_k]]
            result_str = json.dumps(routed, indent=2)
            
            # Save cache
            set_cached_response(cache_key, result_str)
            return CallToolResult(content=[TextContent(type="text", text=result_str)])

        elif name == "filter_context":
            if "text" not in args or "query" not in args:
                return CallToolResult(content=[TextContent(type="text", text="Missing required parameters: text and query")], isError=True)
                
            query = args["query"]
            text_val = args["text"]
            max_chunks = args.get("max_chunks", 3)
            chunk_size = args.get("chunk_size", 500)
            
            # Split document into chunks with overlap
            overlap = 100
            chunks = []
            start = 0
            while start < len(text_val):
                end = min(start + chunk_size, len(text_val))
                chunks.append(text_val[start:end])
                if end == len(text_val):
                    break
                start += chunk_size - overlap
                
            def tokenize(t):
                return set(re.findall(r'\w+', t.lower()))
                
            query_tokens = tokenize(query)
            if not query_tokens:
                result_str = json.dumps(chunks[:max_chunks], indent=2)
                set_cached_response(cache_key, result_str)
                return CallToolResult(content=[TextContent(type="text", text=result_str)])
                
            scored_chunks = []
            for c in chunks:
                chunk_tokens = tokenize(c)
                intersection = query_tokens.intersection(chunk_tokens)
                score = len(intersection)
                scored_chunks.append((score, c))
                
            scored_chunks.sort(key=lambda x: x[0], reverse=True)
            has_any_match = any(sc[0] > 0 for sc in scored_chunks)
            if has_any_match:
                scored_chunks = [sc for sc in scored_chunks if sc[0] > 0]
                
            filtered = [sc[1] for sc in scored_chunks[:max_chunks]]
            result_str = json.dumps(filtered, indent=2)
            
            # Save cache
            set_cached_response(cache_key, result_str)
            return CallToolResult(content=[TextContent(type="text", text=result_str)])

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
