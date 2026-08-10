"""Shared data layer for the AI-READI analysis project.

Notebooks stay thin and import from here, so a fix reaches both papers at
once. Read `docs/CAVEATS.md` before using any of it.

    from aireadi import cohort, omop, azure_io, wearables

    df = cohort.build_core_table()
    cohort.qc_report(df)
"""

from __future__ import annotations

from . import azure_io, cohort, constants, omop, results, wearables
from .constants import (
    CONTAINER_NAME,
    DATASET_VERSION,
    GROUP_ORDER,
    STUDY_ID,
)

__version__ = "0.1.0"

__all__ = [
    "azure_io",
    "cohort",
    "constants",
    "omop",
    "results",
    "wearables",
    "CONTAINER_NAME",
    "DATASET_VERSION",
    "GROUP_ORDER",
    "STUDY_ID",
]
