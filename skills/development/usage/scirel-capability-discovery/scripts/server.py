"""Serve the read-only consumer registry with the official MCP Python SDK.

Install the separately pinned adapter dependencies in mcp-requirements.txt.
This transport adapter has no scientific-runtime dependency. Tool definitions,
validation and snapshot reads belong to consumer_tools, shared with native tools.

Official SDK API: https://py.sdk.modelcontextprotocol.io/advanced/low-level-server/
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import consumer_tools


def create_server(root):
    """Expose the exact transport-neutral registry through official SDK types."""
    import anyio
    from mcp.server import Server
    from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool

    root = Path(root).absolute()

    async def list_tools(context, params):
        return ListToolsResult(tools=[Tool.model_validate(item) for item in consumer_tools.tools()])

    async def call_tool(context, params):
        result = await anyio.to_thread.run_sync(
            consumer_tools.call_tool, root, params.name, params.arguments
        )
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps(
                        result, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                    ),
                )
            ],
            structured_content=result,
            is_error=consumer_tools.is_error_result(result),
        )

    return Server(
        "SciRel public capability consumer",
        instructions=(
            "Read-only public capability discovery and exact document reads. "
            "Retrieval never establishes scientific applicability. Inspect "
            "selected contracts before calling the separately installed library."
        ),
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )


async def serve_stdio(server):
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, required=True, help="Root of one identity-bound consumer runtime"
    )
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("--port must be 1..65535")
    try:
        server = create_server(args.root)
    except ImportError as error:
        parser.exit(
            2,
            "MCP adapter dependency unavailable; install mcp-requirements.txt "
            "in a separate adapter environment. " + str(error) + "\n",
        )
    if args.transport == "stdio":
        import anyio

        anyio.run(serve_stdio, server)
    else:
        import uvicorn

        app = server.streamable_http_app(host=args.host, json_response=True)
        uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
