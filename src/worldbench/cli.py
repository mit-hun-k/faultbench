"""`worldbench` command line. `serve` runs a world.yaml over MCP (stdio or HTTP)."""

import argparse
import sys

from worldbench import __version__
from worldbench.faults import FaultProfile
from worldbench.server import serve_http, serve_stdio


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="worldbench", description=__doc__)
    parser.add_argument("--version", action="version", version=f"worldbench {__version__}")
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="serve a world.yaml over MCP (stdio or HTTP)")
    serve.add_argument("world", help="path to world.yaml")
    serve.add_argument(
        "--http", action="store_true", help="serve over streamable HTTP instead of stdio"
    )
    serve.add_argument("--host", default="127.0.0.1", help="HTTP host (default 127.0.0.1)")
    serve.add_argument("--port", type=int, default=8000, help="HTTP port (default 8000)")
    serve.add_argument("--faults", action="store_true", help="apply the world file's faults: block")
    serve.add_argument("--run-index", type=int, default=0, help="run index for the fault RNG")
    serve.add_argument("--state-file", help="mirror world state to this JSON file after each call")

    args = parser.parse_args(argv)
    if args.command == "serve":
        return _serve(args)
    parser.print_help()
    return 0


def _serve(args: argparse.Namespace) -> int:
    faults = FaultProfile.from_world_file(args.world) if args.faults else None
    if args.http:
        print(
            f"worldbench: serving {args.world} at http://{args.host}:{args.port}/mcp",
            file=sys.stderr,
        )
        serve_http(
            args.world,
            host=args.host,
            port=args.port,
            faults=faults,
            run_index=args.run_index,
            state_file=args.state_file,
        )
    else:
        serve_stdio(
            args.world,
            faults=faults,
            run_index=args.run_index,
            state_file=args.state_file,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
