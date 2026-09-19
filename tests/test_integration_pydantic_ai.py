"""The Pydantic AI adapter (milestone 10), tested keylessly: it builds a toolset for both an
in-process server and a URL, and the in-process one lists the world's tools."""

from pathlib import Path

from faultbench.integrations.pydantic_ai import agent, toolset
from faultbench.server import build_server
from faultbench.world import World

MINI = Path(__file__).parent / "worlds/mini.yaml"


async def test_toolset_from_in_process_server_lists_tools():
    world = World.load(MINI)
    ts = toolset(build_server(world))
    async with ts.client as client:
        names = {t.name for t in await client.list_tools()}
    assert {"get_widget", "sell_widget"} <= names


def test_toolset_from_url_builds():
    # A URL just builds a toolset; no connection until used.
    ts = toolset("http://127.0.0.1:9/mcp")
    assert ts is not None


def test_agent_wires_the_toolset():
    world = World.load(MINI)
    a = agent("test", build_server(world), system_prompt="hi")  # 'test' = keyless built-in model
    assert a is not None  # constructed without a model call
