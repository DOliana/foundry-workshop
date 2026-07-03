"""Lab 04 — MCP server attach helper.

Prints the Microsoft Learn MCP server URL (the public endpoint
participants paste into the portal when adding an MCP tool to an
agent), and — optionally — verifies connectivity with a `list_tools`
call.

Ships **fully commented**. Lab 04 step 1 uncomments this file.

Run (after uncommenting):

    python -m src.labs.lab04.mcp_attach            # just print URL
    python -m src.labs.lab04.mcp_attach --probe    # also list_tools
"""

# from __future__ import annotations
#
# import argparse
# import asyncio
#
# LEARN_MCP_URL = "https://learn.microsoft.com/api/mcp"
#
#
# async def _probe(url: str) -> None:
#     # The `mcp` package ships with the agent-framework install. We use the
#     # SSE / streamable HTTP client to do a one-shot list_tools probe.
#     from mcp import ClientSession
#     from mcp.client.streamable_http import streamablehttp_client
#
#     async with streamablehttp_client(url) as (read, write, _):
#         async with ClientSession(read, write) as session:
#             await session.initialize()
#             tools = await session.list_tools()
#             print(f"  tools advertised by {url}:")
#             for t in tools.tools:
#                 print(f"    - {t.name}")
#
#
# def main() -> None:
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--probe", action="store_true")
#     parser.add_argument("--url", default=LEARN_MCP_URL)
#     args = parser.parse_args()
#
#     print("Paste the following URL into the portal:")
#     print(f"  Agent -> Tools -> + Add -> MCP server  ->  {args.url}")
#     if args.probe:
#         asyncio.run(_probe(args.url))
#
#
# if __name__ == "__main__":
#     main()
