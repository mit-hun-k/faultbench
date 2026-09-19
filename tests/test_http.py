"""HTTP transport + framework-neutrality (milestone 8).

Serves a world over streamable HTTP (via `worldbench serve --http`, spawned by the `mcp_url`
fixture) and drives it with the *reference* `mcp.Client` — a different client stack from the
Pydantic AI agent used elsewhere. That the world is a plain MCP-over-HTTP server any MCP
client can use is the "works with any framework" claim, made keyless and deterministic.
"""

import pytest
from mcp import Client

from worldbench.cli import main as cli_main


@pytest.mark.world("worlds/mini.yaml")
async def test_reference_mcp_client_over_http(mcp_url):
    async with Client(str(mcp_url)) as client:
        listed = await client.list_tools()
        tools = {t.name for t in listed.tools}
        assert {"get_widget", "sell_widget"} <= tools
        await client.call_tool("sell_widget", {"id": "1", "status": "sold"})
        got = await client.call_tool("get_widget", {"id": "1"})
    # Assert on the out-of-process world via its state-file mirror.
    assert mcp_url.snapshot()["widgets"]["1"]["status"] == "sold"
    assert got is not None


def test_cli_serve_requires_world(capsys):
    # `worldbench serve` with no world path exits non-zero (argparse usage error).
    with pytest.raises(SystemExit) as exc:
        cli_main(["serve"])
    assert exc.value.code != 0


def test_cli_help_still_zero():
    assert cli_main([]) == 0
