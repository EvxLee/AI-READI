#!/usr/bin/env python3
"""E1.1 -- population description table (PRESPEC.md, Aim 1 experiments).

Mean/median/IQR for every pre-specified variable (6 environmental, BMI, 8
wearable, CES-D-10), overall and split by diabetes severity group, plus a
Kruskal-Wallis test across the 4 severity groups per variable.

Builds on `cohort.build_core_table()` for everything except two wearable
fields it doesn't carry (`active_calories`, `respiratory_rate`) and the
environmental block (`build_p2_table()` is still a stub -- see its
docstring), which comes from `data/processed/p2/environmental_summary.csv`,
built by `build_env_table.py` in this same folder.

Run `build_env_table.py` first if that file doesn't exist yet.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from aireadi import azure_io, cohort, results, wearables
from aireadi.constants import GROUP_ORDER

ENV_TABLE = Path(__file__).resolve().parents[2] / "data" / "processed" / "p2" / "environmental_summary.csv"

# (column in the merged table, display label)
VARIABLES = [
    ("mean_temp", "Temperature (C)"),
    ("mean_hum", "Humidity (%)"),
    ("mean_light", "Light (lch0)"),
    ("mean_pm25", "PM2.5 (ug/m3)"),
    ("log_pm25", "log(1+PM2.5)"),
    ("mean_voc", "VOC Index"),
    ("mean_nox", "NOx Index"),
    ("bmi", "BMI"),
    ("mean_glucose", "CGM mean glucose (mg/dL)"),
    ("heart_rate", "Heart rate (bpm)"),
    ("stress", "Stress level"),
    ("sleep_hours", "Sleep (hours/night)"),
    ("steps", "Daily steps"),
    ("active_calories", "Active calories (kcal/day)"),
    ("spo2", "Oxygen saturation, SpO2 (%)"),
    ("respiratory_rate", "Respiratory rate (device units)"),
    ("cesd_total", "CES-D-10 total score"),
]


def build_table() -> pd.DataFrame:
    """Core table + the two missing wearable fields + environmental block."""
    df = cohort.build_core_table()

    activity = wearables.clean_garmin_manifest(azure_io.load_table("manifest_activity"))
    activity["person_id"] = activity["person_id"].astype(str)
    extra = activity[["person_id", "average_active_calories_kcal", "average_respiratory_rate_bpm"]].rename(
        columns={
            "average_active_calories_kcal": "active_calories",
            "average_respiratory_rate_bpm": "respiratory_rate",
        }
    )
    df = df.merge(extra, on="person_id", how="left")

    if not ENV_TABLE.exists():
        raise FileNotFoundError(
            f"{ENV_TABLE} not found -- run build_env_table.py first."
        )
    env = pd.read_csv(ENV_TABLE, dtype={"person_id": str})
    df = df.merge(
        env[["person_id", "mean_temp", "mean_hum", "mean_light", "mean_pm25", "mean_voc", "mean_nox"]],
        on="person_id", how="left",
    )
    df["log_pm25"] = np.log1p(df["mean_pm25"])
    return df


def describe(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col, label in VARIABLES:
        if col not in df.columns:
            continue
        overall = df[col].dropna()
        row = {
            "variable": label,
            "n": int(overall.shape[0]),
            "mean": overall.mean(),
            "median": overall.median(),
            "p25": overall.quantile(0.25),
            "p75": overall.quantile(0.75),
        }

        group_values = []
        for g in GROUP_ORDER:
            sub = df.loc[df["study_group_label"] == g, col].dropna()
            row[f"{g}_n"] = int(sub.shape[0])
            row[f"{g}_mean"] = sub.mean()
            row[f"{g}_median"] = sub.median()
            if len(sub) > 0:
                group_values.append(sub.values)

        if len(group_values) > 1:
            h, p = stats.kruskal(*group_values)
            row["kruskal_H"], row["kruskal_p"] = h, p
        else:
            row["kruskal_H"], row["kruskal_p"] = np.nan, np.nan

        rows.append(row)

    return pd.DataFrame(rows).set_index("variable")


def main() -> None:
    df = build_table()
    table = describe(df)

    pd.set_option("display.width", 200)
    print(table.round(3).to_string())

    n_sig = int((table["kruskal_p"] < 0.05).sum())
    result_summary = (
        f"N={len(df)} participants merged (core+wearable+environmental). "
        f"{n_sig}/{len(table)} variables differ significantly (p<0.05, Kruskal-Wallis) "
        f"across the 4 severity groups."
    )

    path = results.save(
        "E1.1", table, paper="p2",
        method="Descriptive stats (n/mean/median/IQR overall; n/mean/median by "
               "severity group; Kruskal-Wallis across groups) for all 17 pre-specified "
               "variables (PRESPEC.md sections 3-4), built on cohort.build_core_table() "
               "plus environmental_summary.csv",
        result=result_summary,
        decision="keep",
    )
    print(f"\nSaved to {path}")
    print(f"Logged in {results.log_path('p2')}")


if __name__ == "__main__":
    main()
