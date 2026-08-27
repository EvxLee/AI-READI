"""Shared entry point for every Phase-2 runner.

Phase 2 runs on exactly the Phase-1 analysis dataset plus the derived outcome
columns the standard recipe needs, so `load()` is `_phase1.load()` with
`associations.add_outcome_columns` applied. One place decides that, so E2C.1
through E2F.1 cannot drift apart -- and so a Phase-2 result can always be
traced back to the same 2,280-row table Phase 1 published from.

Nothing here is analysis. The recipe itself is `aireadi.associations`.
"""

from __future__ import annotations

import pandas as pd

from aireadi import associations

import _phase1

banner = _phase1.banner


def load(**cutoffs) -> pd.DataFrame:
    """The Phase-1 table with Phase-2 outcome columns added."""
    return associations.add_outcome_columns(_phase1.load(**cutoffs))


def print_table(df: pd.DataFrame, *, title: str = "") -> None:
    """Print a result table with p-values in scientific notation.

    `.to_string()` on a frame holding p ~ 1e-20 alongside percentages renders
    the small ones as 0.000000, which reads as a bug and throws away the
    magnitude. Phase 1 hit this and fixed it in `stats`; the same rule applies
    to anything printed here.
    """
    if title:
        print(f"\n{title}")
    show = df.copy()
    for col in ("p", "q"):
        if col in show.columns:
            show[col] = show[col].map(lambda v: "" if pd.isna(v) else f"{v:.3g}")
    pd.set_option("display.width", 220)
    print(show.to_string())


def headline(df: pd.DataFrame, *, adjustment: str = "damage",
             alpha: float = 0.05, use_q: bool = True) -> pd.DataFrame:
    """Rows that survive the primary family's correction.

    Defaults to q < 0.05 within the adjusted family, which is what Phase 3
    should rank on. Passing `use_q=False` gives the uncorrected view -- useful
    to state in a log entry how much of an apparent signal the correction ate.
    """
    sel = df
    if "adjustment" in df.index.names:
        sel = df.xs(adjustment, level="adjustment", drop_level=False)
    elif "adjustment" in df.columns:
        sel = df[df["adjustment"] == adjustment]
    col = "q" if use_q else "p"
    return sel[sel[col] < alpha].sort_values(col)


def summarise(df: pd.DataFrame, *, limit: int = 8) -> str:
    """One-line summary of surviving rows, for a `results.save()` entry.

    Truncates with an explicit count rather than silently, so a log line can
    never imply it listed everything when it did not.
    """
    if not len(df):
        return "none"
    parts = []
    for idx, row in df.head(limit).iterrows():
        exposure = row.get("exposure_label", idx[0] if isinstance(idx, tuple) else idx)
        outcome = row.get("outcome_label", idx[1] if isinstance(idx, tuple) else "")
        parts.append(f"{exposure} -> {outcome}: {row['estimate']} "
                     f"({row['ci_lo']}-{row['ci_hi']}), q={row['q']:.3g}")
    text = "; ".join(parts)
    if len(df) > limit:
        text += f"; and {len(df) - limit} more"
    return text
