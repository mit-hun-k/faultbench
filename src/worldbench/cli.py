"""`worldbench` command line. Milestone 8 adds `serve`."""

import argparse
import sys

from worldbench import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="worldbench", description=__doc__)
    parser.add_argument("--version", action="version", version=f"worldbench {__version__}")
    sub = parser.add_subparsers(dest="command")
    serve = sub.add_parser("serve", help="serve a world.yaml over MCP (milestone 8)")
    serve.add_argument("world", help="path to world.yaml")
    args = parser.parse_args(argv)
    if args.command == "serve":
        print("worldbench serve: not implemented yet (milestone 8)", file=sys.stderr)
        return 2
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
