"""`python -m worldbench.server <world.yaml>` — serve a world over stdio.

A thin entry so an agent (or a test) can spawn a generated MCP server as a subprocess.
Set WORLDBENCH_STATE_FILE to have the server mirror world state to a JSON file after every
call (used by the shop demo to inspect end state).
"""

from __future__ import annotations

import os
import sys

from .mcp_server import serve_stdio


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python -m worldbench.server <world.yaml>", file=sys.stderr)
        return 2
    serve_stdio(argv[0], state_file=os.environ.get("WORLDBENCH_STATE_FILE"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
