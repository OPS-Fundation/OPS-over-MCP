import asyncio
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "server" / "mcp_ops_server.py"


async def main() -> None:
    server_params = StdioServerParameters(
        command="python",
        args=[str(SERVER_PATH)],
        env={**os.environ},
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("\n== list_tools ==")
            for t in tools.tools:
                print("-", t.name)

            print("\n== ops.list ==")
            r1 = await session.call_tool("ops_list", {})
            print(r1)

            print("\n== ops.get ==")
            r2 = await session.call_tool("ops_get", {"ref": "ops.lead_outreach@1.x"})
            print(r2)

            print("\n== ops.render ==")
            r3 = await session.call_tool(
                "ops_render",
                {
                    "ref": "ops.lead_outreach@1.x",
                    "variables": {
                        "lead_name": "Ana",
                        "company": "TechNova",
                        "role": "Head of Operations",
                        "value_prop": "Reduce onboarding time by 35% using automated workflow intelligence.",
                        "context_snippets": [
                            "TechNova is hiring ops analysts and expanding in LATAM.",
                            "They use HubSpot and Slack for internal workflows."
                        ],
                    },
                    "options": {
                        "token_budget": 650,
                        "format": "messages",
                        "redact": True,
                        "include_lineage": True
                    },
                },
            )
            print(r3)


if __name__ == "__main__":
    asyncio.run(main())
