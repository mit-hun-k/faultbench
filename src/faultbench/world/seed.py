"""Deterministic seed data generation (faker) and CSV/JSON loaders. Milestone 2.

Invariant: same YAML + same world seed => byte-identical initial state, on any day and in
any process. Two things make that hold:
  - every RNG (faker and the stdlib Random) is seeded from `f"{world.seed}:{record}..."`,
    a stable string seed, and fields are generated in YAML declaration order;
  - datetimes are drawn from a FIXED absolute window, never a now-relative one, so the
    output does not drift with the wall clock.
"""

from __future__ import annotations

import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from faker import Faker

from .schema import FieldType, RecordType

if TYPE_CHECKING:
    from .engine import Table, World

# The world's reference "now": a fixed anchor so seeding is wall-clock-independent, and so a
# FakeClock at this instant sees the data as recent. MUST equal faults.clock.DEFAULT_NOW
# (guarded by a test) so time-dependent rules (e.g. a 30-day return window) have eligible
# records at the default clock. Generated datetimes fall in the 20 days ending at the anchor.
WORLD_EPOCH = datetime(2025, 6, 1)
_DT_END = WORLD_EPOCH
_DT_START = WORLD_EPOCH - timedelta(days=20)


def seed_table(table: Table, record_type: RecordType, count: int, world: World) -> None:
    """Generate `count` rows into `table`, deterministically."""
    fake = Faker()
    fake.seed_instance(f"{world.seed}:{record_type.name}")
    rng = random.Random(f"{world.seed}:{record_type.name}:rng")
    for i in range(1, count + 1):
        row: dict[str, Any] = {}
        for fname, ftype in record_type.fields.items():
            row[fname] = str(i) if fname == "id" else _gen(ftype, fake, rng, world)
        table._seed_insert(row)


def _gen(ft: FieldType, fake: Faker, rng: random.Random, world: World) -> Any:
    if ft.kind == "str":
        return fake.word()
    if ft.kind == "int":
        return rng.randint(0, 1000)
    if ft.kind == "float":
        return round(rng.uniform(0, 1000), 2)
    if ft.kind == "bool":
        return rng.random() < 0.5
    if ft.kind == "datetime":
        return fake.date_time_between(start_date=_DT_START, end_date=_DT_END).isoformat()
    if ft.kind == "enum":
        return rng.choice(ft.enum_members)
    if ft.kind == "ref":
        target = world.table(ft.ref_record)
        ids = list(target._rows.keys())
        return rng.choice(ids) if ids else ""
    raise ValueError(f"cannot generate a value for field kind {ft.kind!r}")


def load_rows(path: str | Path) -> list[dict[str, Any]]:
    """Load seed rows from a .json (list of objects) or .csv file."""
    path = Path(path)
    if path.suffix == ".json":
        data = json.loads(path.read_text())
        if not isinstance(data, list):
            raise ValueError(f"{path}: JSON seed must be a list of objects")
        return data
    if path.suffix == ".csv":
        with path.open(newline="") as fh:
            return list(csv.DictReader(fh))
    raise ValueError(f"{path}: unsupported seed file type (use .json or .csv)")
