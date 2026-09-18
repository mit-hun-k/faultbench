"""`python -m worldbench.server <world.yaml> [--faults]` — serve a world over stdio.

A thin entry so an agent (or a test) can spawn a generated MCP server as a subprocess.
Env:
  WORLDBENCH_STATE_FILE  mirror world state to this JSON file after every call (demo uses it)
  WORLDBENCH_FAULTS=1    turn on the world file's `faults:` block (same as --faults)
  WORLDBENCH_RUN_INDEX   run index for the fault RNG (default 0)
"""

from __future__ import annotations

import os
import sys

from ..faults import FaultProfile
from .mcp_server import serve_stdio


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    args = [a for a in argv if not a.startswith("-")]
    flags = {a for a in argv if a.startswith("-")}
    if len(args) != 1:
        print("usage: python -m worldbench.server <world.yaml> [--faults]", file=sys.stderr)
        return 2
    world_path = args[0]
    faults = None
    if "--faults" in flags or os.environ.get("WORLDBENCH_FAULTS") == "1":
        faults = FaultProfile.from_world_file(world_path)
    run_index = int(os.environ.get("WORLDBENCH_RUN_INDEX", "0"))
    serve_stdio(
        world_path,
        state_file=os.environ.get("WORLDBENCH_STATE_FILE"),
        faults=faults,
        run_index=run_index,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
