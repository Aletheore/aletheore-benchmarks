"""Real MCP stdio client: launches a given server subprocess, does the real
initialize handshake, lists tools, and calls a tool - capturing exactly what
a real calling agent would receive as tool-result text."""
import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run(command, args, env, tool_name, tool_args):
    params = StdioServerParameters(command=command, args=args, env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, tool_args)
            text = "\n".join(
                c.text for c in result.content if hasattr(c, "text")
            )
            return text


async def list_tools(command, args, env):
    params = StdioServerParameters(command=command, args=args, env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            return [t.name for t in tools.tools]


if __name__ == "__main__":
    import json as _json
    mode = sys.argv[1]
    if mode == "list":
        command, *args = sys.argv[2:]
        names = asyncio.run(list_tools(command, args, None))
        print(_json.dumps(names))
    else:
        command = sys.argv[2]
        rest = sys.argv[3:]
        # format: <command> <args...> -- <tool_name> <json_args>
        sep = rest.index("--")
        args = rest[:sep]
        tool_name = rest[sep + 1]
        tool_args = _json.loads(rest[sep + 2])
        text = asyncio.run(run(command, args, None, tool_name, tool_args))
        print(text)
