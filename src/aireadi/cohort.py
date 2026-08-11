"""Participant-level table builders -- one row per participant.

`build_core_table` assembles the variables both papers share. Each paper then
adds its own outcome block on top:

* Paper 1 (organ damage): `build_p1_table`
* Paper 2 (environment / depression): `build_p2_table`

Nothing here writes to disk. Callers decide where a table lands, and any
person_id-keyed output belongs under `data/processed/` (gitignored).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import azure_io, omop, wearables
from .constants import (
    ACR_UNIT_SCALE,
    CESD_CUTOFF,
    EXPECTED_GROUP_N,
    EXPECTED_TOTAL_N,
    GROUP_CODE_TO_LABEL,
    GROUP_ORDER,
    GROUP_STR_TO_CODE,
    MEASUREMENT_KEYS,
    MONOFILAMENT_MAX_SITES,
    OBSERVATION_KEYS,
    ORGAN_SELF_REPORT,
    P1_MEASUREMENT_KEYS,
    PAID5_CUTOFF,
)

__all__ = [
    "load_participants",
    "build_core_table",
    "build_p1_table",
    "build_p2_table",
    "find_items",
    "qc_report",
]

# Ages are derived from year_of_birth against the data-collection midpoint;
# the public release carries no finer date of birth.
_AGE_REFERENCE_YEAR = 2024


def load_participants() -> pd.DataFrame:
    """participants.tsv with severity coded and site/age attached.

    Columns: person_id, study_group_code (0-3), study_group_label (ordered
    categorical), clinical_site, age.
    """
    parts = azure_io.load_table("participants")
    parts.columns = parts.columns.str.strip().str.lower()
    parts["person_id"] = parts["person_id"].astype(str)

    group_col = next(
        (c for c in parts.columns if "study_group" in c or c == "study_group"), None
    )
    if group_col is None:
        group_col = next((c for c in parts.columns if "group" in c), None)
    if group_col is None:
        raise KeyError(f"No study-group column in participants.tsv: {list(parts.columns)}")

    codes = (
        parts[group_col].astype(str).str.lower().str.strip().map(GROUP_STR_TO_CODE)
    )
    unmapped = parts.loc[codes.isna(), group_col].unique()
    if len(unmapped):
        raise ValueError(
            f"Unmapped study-group values {list(unmapped)}; add them to "
            "constants.GROUP_STR_TO_CODE rather than guessing downstream."
        )
    parts["study_group_code"] = codes.astype(int)
    parts["study_group_label"] = pd.Categorical(
        parts["study_group_code"].map(GROUP_CODE_TO_LABEL),
        categories=GROUP_ORDER, ordered=True,
    )

    site_col = next((c for c in parts.columns if "site" in c), None)
    parts["clinical_site"] = parts[site_col] if site_col else pd.NA

    keep = ["person_id", "study_group_code", "study_group_label", "clinical_site"]
    if "age" in parts.columns:
        parts["age"] = pd.to_numeric(parts["age"], errors="coerce")
        keep.append("age")
    out = parts[keep].copy()

    if "age" not in out.columns:
        person = azure_io.load_table("person", usecols=["person_id", "year_of_birth"])
        person["person_id"] = person["person_id"].astype(str)
        person["age"] = _AGE_REFERENCE_YEAR - pd.to_numeric(
            person["year_of_birth"], errors="coerce"
        )
        out = out.merge(person[["person_id", "age"]], on="person_id", how="left")

    return out


def build_core_table(*, include_wearables: bool = True) -> pd.DataFrame:
    """The participant-level table both papers build on.

    One row per participant: severity, age, site, BMI, HbA1c, CES-D-10,
    PAID-5, comorbidity count, and (optionally) CGM mean glucose plus Garmin
    summaries.

    Every survey value passes through the 555/777/99 cleaning in `omop`.
    """
    df = load_participants()

    observation = azure_io.load_table(
        "observation",
        usecols=["person_id", "observation_source_value", "value_as_number"],
    )
    obs = omop.add_item_key(observation)

    measurement = azure_io.load_table("measurement")
    measurement["person_id"] = measurement["person_id"].astype(str)

    # ── Survey scores ───────────────────────────────────────────────────
    series = [
        omop.first_value(obs, OBSERVATION_KEYS["cesd_total"], name="cesd_total"),
        omop.first_value(obs, OBSERVATION_KEYS["paid_total"], name="paid_total"),
        omop.first_value(obs, OBSERVATION_KEYS["education_years"], name="education_years"),
        omop.comorbidity_count(obs),
    ]
    for s in series:
        df = df.merge(s.reset_index(), on="person_id", how="left")

    # ── Labs and vitals ─────────────────────────────────────────────────
    for name, key in (("hba1c", MEASUREMENT_KEYS["hba1c"]),
                      ("bmi", MEASUREMENT_KEYS["bmi"]),
                      ("moca_total", MEASUREMENT_KEYS["moca_total"])):
        lab = omop.extract_lab(measurement, key, name=name)
        if not lab.empty:
            df = df.merge(lab, on="person_id", how="left")
        else:
            df[name] = np.nan

    # ── Screen-positive flags ───────────────────────────────────────────
    df["cesd_positive"] = _threshold_flag(df["cesd_total"], CESD_CUTOFF)
    df["paid_positive"] = _threshold_flag(df["paid_total"], PAID5_CUTOFF)

    if include_wearables:
        df = _attach_wearables(df)

    return df


def _threshold_flag(values: pd.Series, cutoff: float) -> pd.Series:
    """Binary at-or-above flag that keeps NaN as NaN.

    A plain `.astype(float)` on the comparison would silently turn every
    missing score into a negative screen.
    """
    return values.ge(cutoff).astype("float").mask(values.isna())


def _attach_wearables(df: pd.DataFrame) -> pd.DataFrame:
    """Merge CGM mean glucose and cleaned Garmin summaries onto `df`."""
    cgm = azure_io.load_table("manifest_cgm")
    cgm.columns = cgm.columns.str.strip().str.lower()
    cgm["person_id"] = cgm["person_id"].astype(str)
    if "average_glucose_level_mg_dl" in cgm.columns:
        df = df.merge(
            cgm[["person_id", "average_glucose_level_mg_dl"]]
            .rename(columns={"average_glucose_level_mg_dl": "mean_glucose"}),
            on="person_id", how="left",
        )

    activity = wearables.clean_garmin_manifest(azure_io.load_table("manifest_activity"))
    garmin_cols = {
        "average_daily_activity": "steps",
        "average_heartrate_bpm": "heart_rate",
        "average_stress_level": "stress",
        "average_sleep_hours": "sleep_hours",
        "average_oxygen_saturation_pct": "spo2",
    }
    present = {k: v for k, v in garmin_cols.items() if k in activity.columns}
    if present:
        df = df.merge(
            activity[["person_id", *present]].rename(columns=present),
            on="person_id", how="left",
        )
    return df


def build_p1_table(markers: dict[str, str] | None = None) -> pd.DataFrame:
    """Paper 1: core table plus the three organ-damage markers and their
    self-report comparators.

    The marker keys were confirmed in E0.1 and live in
    `constants.P1_MEASUREMENT_KEYS`; the organ-to-self-report mapping was
    confirmed in E0.2 and lives in `constants.ORGAN_SELF_REPORT`. Pass
    `markers` only to override them for a sensitivity run.

    Adds, on top of `build_core_table()`:

    * `urine_albumin`, `urine_creatinine`, `acr_mg_g` -- kidney
    * `troponin_t`, `troponin_t_below_detection` -- heart
    * `monofilament_left`, `monofilament_right`, `monofilament_min`,
      `monofilament_insensate_sites` -- nerve
    * `sr_kidney`, `sr_heart` -- self-reported diagnosis flags (0/1, NaN when
      refused). There is deliberately no `sr_nerve`: no such item exists.

    No abnormality thresholds are applied here. Which cutoff defines "abnormal"
    is an analysis choice that belongs in PRESPEC.md and is swept in E1.5, not
    baked into the data layer.
    """
    df = build_core_table()

    keys = dict(P1_MEASUREMENT_KEYS)
    if markers:
        keys.update(markers)

    measurement = azure_io.load_table("measurement")
    measurement["person_id"] = measurement["person_id"].astype(str)

    for name, key in keys.items():
        lab = omop.extract_lab(
            measurement, key, name=name,
            flag_below_detection="troponin" in name.lower(),
        )
        if lab.empty:
            raise ValueError(
                f"No measurement rows for marker {name!r} (key {key!r}). "
                "Confirm the key with find_items() before building the table."
            )
        df = df.merge(lab, on="person_id", how="left")

    df = _add_kidney_acr(df)
    df = _add_monofilament_summary(df)
    df = _add_self_report_flags(df)
    return df


def _add_kidney_acr(df: pd.DataFrame) -> pd.DataFrame:
    """Albumin-to-creatinine ratio in mg/g.

    Both source fields carry the same unit, so the ratio is dimensionless and
    the x1000 puts it on the conventional mg/g scale. A urine creatinine of
    zero is a void too dilute to interpret, not an infinite ratio -- those
    become NaN rather than inf, which would otherwise survive every downstream
    threshold comparison as "abnormal".
    """
    alb, creat = df.get("urine_albumin"), df.get("urine_creatinine")
    if alb is None or creat is None:
        return df
    denom = creat.where(creat > 0)
    df["acr_mg_g"] = alb / denom * ACR_UNIT_SCALE
    return df


def _add_monofilament_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per-participant monofilament summaries across both feet.

    The exam records sites felt out of 10 per foot. `monofilament_min` is the
    worse foot, and `monofilament_insensate_sites` counts sites not felt across
    both feet (0-20). Loss of protective sensation is conventionally a
    per-foot judgement, so the worse foot is the natural participant-level
    summary; the exact cutoff is a PRESPEC decision.
    """
    left, right = df.get("monofilament_left"), df.get("monofilament_right")
    if left is None or right is None:
        return df
    df["monofilament_min"] = df[["monofilament_left", "monofilament_right"]].min(axis=1)
    df["monofilament_insensate_sites"] = (
        (MONOFILAMENT_MAX_SITES - left) + (MONOFILAMENT_MAX_SITES - right)
    )
    return df


def _add_self_report_flags(df: pd.DataFrame) -> pd.DataFrame:
    """One `sr_<organ>` flag per organ that has a self-report comparator.

    An organ's flag is 1 if the participant answered yes to any of its items.
    Refusals (777) are already NaN via the survey cleaning, and a participant
    who refused every item for an organ stays NaN rather than becoming a
    silent "no" -- the difference between "never told" and "would not say"
    is exactly what an unawareness estimate must not blur.

    `ORGAN_SELF_REPORT["nerve"]` is empty by design: E0.2 established that no
    neuropathy item exists in this release, so no `sr_nerve` column is created.
    """
    observation = azure_io.load_table(
        "observation",
        usecols=["person_id", "observation_source_value", "value_as_number"],
    )
    obs = omop.add_item_key(observation)

    for organ, items in ORGAN_SELF_REPORT.items():
        if not items:
            continue
        wide = omop.pivot_items(obs, keys=items)
        present = [c for c in items if c in wide.columns]
        if not present:
            raise ValueError(
                f"None of the self-report items {items!r} for organ {organ!r} "
                "are present; re-run E0.2 before trusting this table."
            )
        flag = wide[present].max(axis=1).clip(upper=1).rename(f"sr_{organ}")
        df = df.merge(flag.reset_index(), on="person_id", how="left")
    return df


def build_p2_table() -> pd.DataFrame:
    """Paper 2: core table plus personal environmental exposure.

    Placeholder. The environmental block (PM2.5, VOC, NOx, temperature,
    humidity, light) is Parwaan's to define, and the per-participant sensor
    CSVs are large enough that the aggregation strategy should be his call.
    Building on `build_core_table()` means a fix to the shared survey or
    wearable logic reaches both papers.

    When implementing: log-transform PM2.5 (median ~3, max ~1,178 ug/m3) and
    drop the sensor that logged 1,145 C.
    """
    raise NotImplementedError(
        "P2 environmental aggregation not implemented yet -- see "
        "papers/p2-env-depression/PLAN.md. build_core_table() is ready to "
        "build on."
    )


def find_items(pattern: str, *, table: str = "observation",
               regex: bool = True) -> pd.DataFrame:
    """Search a clinical table's item keys and descriptions.

    The discovery tool for Phase 0. Returns item_key, description, and the
    number of participants with a non-missing value, so you can tell a
    full-cohort item from a skip-gated one.

        find_items("albumin|creatinine", table="measurement")
        find_items("kidney|renal|dialysis")
    """
    df = azure_io.load_table(table)
    df["person_id"] = df["person_id"].astype(str)
    source_col = (
        "observation_source_value" if table == "observation"
        else "measurement_source_value"
    )
    keyed = omop.add_item_key(df, source_col=source_col)
    descriptions = omop.item_descriptions(df, source_col=source_col)

    hits = keyed[
        keyed[source_col].astype(str).str.contains(pattern, case=False, regex=regex, na=False)
    ]
    if hits.empty:
        return pd.DataFrame(columns=["item_key", "description", "n_participants",
                                     "n_rows", "val_min", "val_max"])

    summary = (
        hits.groupby("item_key")
        .agg(
            n_participants=("person_id", "nunique"),
            n_rows=("person_id", "size"),
            val_min=("value_clean", "min"),
            val_max=("value_clean", "max"),
        )
        .reset_index()
    )
    summary["description"] = summary["item_key"].map(descriptions)
    return summary[["item_key", "description", "n_participants", "n_rows",
                    "val_min", "val_max"]].sort_values("n_participants", ascending=False)


def qc_report(df: pd.DataFrame, *, strict: bool = False) -> pd.DataFrame:
    """Check a built table against the expected v3.0.0 cohort and report gaps.

    Prints the group-N check and returns a per-column missingness table. A
    group-N mismatch usually means the wrong container or a new release --
    with `strict=True` it raises instead of warning.
    """
    total = len(df)
    print(f"Rows: {total:,} (expected {EXPECTED_TOTAL_N:,})")
    if total != EXPECTED_TOTAL_N:
        msg = f"Row count {total:,} != expected {EXPECTED_TOTAL_N:,}"
        if strict:
            raise AssertionError(msg)
        print(f"  WARNING: {msg}")

    if "study_group_label" in df.columns:
        counts = df["study_group_label"].value_counts().reindex(GROUP_ORDER)
        print("\nSeverity group Ns:")
        for group in GROUP_ORDER:
            got = int(counts.get(group, 0))
            want = EXPECTED_GROUP_N[group]
            mark = "ok" if got == want else "MISMATCH"
            print(f"  {group:<10} {got:>5,}  (expected {want:,})  {mark}")
            if got != want and strict:
                raise AssertionError(f"{group}: {got} != {want}")

    missing = pd.DataFrame({
        "n_present": df.notna().sum(),
        "pct_present": (df.notna().mean() * 100).round(1),
    }).sort_values("pct_present")
    print(f"\nColumn coverage (worst first):\n{missing.to_string()}")
    return missing
