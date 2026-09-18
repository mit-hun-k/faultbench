"""Test setup for the shop example: load .env so a model key is available, and keep the
Pydantic AI banner quiet. Runs when pytest collects `examples/shop`."""

import os
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
_load_dotenv()
