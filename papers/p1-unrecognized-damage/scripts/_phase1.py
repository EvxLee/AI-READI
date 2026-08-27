"""Shared entry point for every Phase-1 runner.

One place decides what "the Phase 1 analysis dataset" means, so E1.1 through
E1.5 cannot silently drift apart. Runners import `load()`; nothing else here
is analysis.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from aireadi import azure_io, cohort, thresholds

MASTER = azure_io.repo_root() / "data" / "processed" / "p1" / "master_table.parquet"


def load(*, rebuild: bool = False, **cutoffs) -> pd.DataFrame:
    """The master participant table with Phase-1 damage flags applied.

    Reads the cached build unless `rebuild=True` (or the cache is absent), in
    which case it rebuilds from the raw tables and re-caches. `cutoffs` are
    passed straight to `thresholds.add_damage_flags`, so a sensitivity run is
    `load(troponin_ng_l=16)`.
    """
    if rebuild or not MASTER.exists():
        df = cohort.build_p1_table()
        MASTER.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(MASTER)          # gitignored: participant-level
    else:
        df = pd.read_parquet(MASTER)

    if len(df) != 2280:
        raise AssertionError(f"master table has {len(df)} rows, expected 2,280")
    return thresholds.add_damage_flags(df, **cutoffs)


def banner(experiment: str, title: str) -> None:
    print("=" * 78)
    print(f"{experiment} — {title}")
    print("=" * 78)


def rebuild_requested() -> bool:
    return "--rebuild" in sys.argv
