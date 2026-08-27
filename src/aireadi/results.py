"""Save an experiment's output and log it, in one call.

Every experiment produces three things: an artifact (figure or table), a line
in the paper's status tracker, and an entry in its log. Doing those as three
separate manual steps is how a log drifts out of sync with what was actually
run -- and the completeness of that log is what defends the paper against the
cherry-picking critique.

    from aireadi import results

    results.save("E1.2", fig, paper="p1",
                 method="Unrecognized fraction per organ, by severity group",
                 result="Kidney 72%, nerve 45%, heart 61% unrecognized",
                 decision="keep")

For a run that produced no artifact -- a null worth recording -- pass None,
or use `log()`.

Saving a table refuses outright if it contains a `person_id` column. Nothing
keyed to a participant may enter a committed folder.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pandas as pd

from .azure_io import repo_root

__all__ = ["save", "log", "results_dir", "log_path"]

PAPER_DIRS = {"p1": "p1-unrecognized-damage", "p2": "p2-env-depression"}

# Columns that make a table participant-level. Anything with one of these is
# individual data and belongs in data/processed/, never papers/*/results/.
IDENTIFYING_COLUMNS = {"person_id", "participant_id", "subject_id"}


def _paper_dir(paper: str) -> Path:
    key = paper.lower().strip()
    if key not in PAPER_DIRS:
        raise ValueError(f"paper must be one of {sorted(PAPER_DIRS)}, got {paper!r}")
    return repo_root() / "papers" / PAPER_DIRS[key]


def results_dir(paper: str) -> Path:
    """The paper's results folder, created if absent."""
    d = _paper_dir(paper) / "results"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_path(paper: str) -> Path:
    """The paper's RESULTS_LOG.md."""
    return _paper_dir(paper) / "RESULTS_LOG.md"


def _slug(experiment_id: str) -> str:
    """E2C.1 -> E2C_1, so IDs survive as filenames."""
    return re.sub(r"[^A-Za-z0-9]+", "_", experiment_id.strip()).strip("_")


def _check_not_participant_level(df: pd.DataFrame, experiment_id: str) -> None:
    found = IDENTIFYING_COLUMNS & {c.lower() for c in df.columns}
    if found:
        raise ValueError(
            f"Refusing to save {experiment_id}: table has {sorted(found)}, making it "
            f"participant-level. papers/*/results/ takes aggregates only. Either "
            f"aggregate first, or write it to data/processed/ instead."
        )


def save(experiment_id: str, artifact=None, *, paper: str, method: str,
         result: str, decision: str, name: str | None = None,
         primary: bool = True) -> Path | None:
    """Write an experiment's artifact and record it in RESULTS_LOG.md.

    `artifact` may be a matplotlib Figure, a pandas DataFrame or Series, or
    None for a run with nothing to save. `decision` is normally "keep",
    "kill", or "rescope".

    An experiment often produces several artifacts. Every one of them gets its
    own entry in the log, but the STATUS TABLE has a single row per ID, and
    whichever call ran last would otherwise own it -- so E1.2's row ended up
    advertising a secondary table instead of the headline. Pass
    `primary=False` on the supporting artifacts; only the primary one writes
    the status row.

    Returns the path written, or None if there was no artifact.
    """
    slug = _slug(experiment_id)
    suffix = f"_{_slug(name)}" if name else ""
    path: Path | None = None

    if artifact is not None:
        if isinstance(artifact, pd.Series):
            artifact = artifact.to_frame()

        if isinstance(artifact, pd.DataFrame):
            _check_not_participant_level(artifact, experiment_id)
            path = results_dir(paper) / f"{slug}{suffix}.csv"
            artifact.to_csv(path, index=True)
        elif hasattr(artifact, "savefig"):
            path = results_dir(paper) / f"{slug}{suffix}.png"
            artifact.savefig(path, dpi=200, bbox_inches="tight")
        else:
            raise TypeError(
                f"Cannot save {type(artifact).__name__}; pass a DataFrame, a "
                "matplotlib Figure, or None."
            )

    _append_log(paper, experiment_id, method, result, decision, path)
    if primary:
        _update_status_row(paper, experiment_id, result, decision, path)
    return path


def log(experiment_id: str, *, paper: str, method: str, result: str,
        decision: str) -> None:
    """Record a run that produced no artifact. A null still gets logged."""
    save(experiment_id, None, paper=paper, method=method, result=result,
         decision=decision)


def _append_log(paper: str, experiment_id: str, method: str, result: str,
                decision: str, path: Path | None) -> None:
    entry = (
        f"\n### {experiment_id} — {date.today().isoformat()}\n"
        f"**Method:** {method}\n"
        f"**Result:** {result}\n"
        f"**Decision:** {decision}\n"
        f"**Output:** {'results/' + path.name if path else 'none'}\n"
    )
    target = log_path(paper)
    with open(target, "a", encoding="utf-8") as fh:
        fh.write(entry)


def _update_status_row(paper: str, experiment_id: str, result: str,
                       decision: str, path: Path | None) -> None:
    """Fill in this experiment's row in the status table, if it has one.

    Silently does nothing when the ID is not already tracked -- an ad-hoc
    sub-question still gets a log entry, it just has no pre-made row.
    """
    target = log_path(paper)
    if not target.exists():
        return

    text = target.read_text(encoding="utf-8")
    escaped = re.escape(experiment_id)
    pattern = re.compile(rf"^\|\s*{escaped}\s*\|[^\n]*$", re.MULTILINE)
    if not pattern.search(text):
        return

    output = f"`results/{path.name}`" if path else "—"
    row = (f"| {experiment_id} | done | {output} | "
           f"{_escape_cell(result)} | {_escape_cell(decision)} |")
    target.write_text(pattern.sub(lambda _: row, text, count=1), encoding="utf-8")


def _escape_cell(value: str) -> str:
    """Keep a value from breaking the markdown table it lands in."""
    return value.replace("|", "\\|").replace("\n", " ").strip()
