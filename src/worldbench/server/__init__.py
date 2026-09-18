"""worldbench.server — see docs/ARCHITECTURE.md."""

from .mcp_server import build_server, serve_stdio
from .operations import resolve_handler, run_builtin

__all__ = ["build_server", "serve_stdio", "run_builtin", "resolve_handler"]
