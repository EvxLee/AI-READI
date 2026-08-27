"""Shared entry point for the Phase-3 runners (E3.1 ranking, E3.3 confirmatory).

Phase 3 has to look at *every* Phase-2 exposure at once — to rank them (E3.1)
and to rerun the promoted ones per `PRESPEC.md` (E3.3) — so the derived
exposures that Phase 2 built one track at a time are attached here in one
place: CGM metrics, ECG numeric metrics, PhenX SDOH scores, the glycaemia/label
discordance flags and the either-organ unrecognized outcome. Each is built
exactly as its Phase-2 runner built it (same source, same cleaning, same
column names), so an E3 number can always be traced back to the E2 artifact
it is meant to reproduce.

Also here: the per-site refit that the plan's "consistent across the three
sites" criterion needs, and the PRESPEC reader that E3.3 runs against so the
spec and the code cannot drift.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as _sps

from aireadi import associations, azure_io, omop, thresholds

import _phase1
import _phase2

banner = _phase1.banner
print_table = _phase2.print_table

PAPER = azure_io.repo_root() / "papers" / "p1-unrecognized-damage"
RESULTS = PAPER / "results"
PRESPEC = PAPER / "PRESPEC.md"
SITES = ["UW", "UAB", "UCSD"]

# E2A.2's external cutoffs, restated here so E3 uses the identical values.
HBA1C_DIABETES = 6.5
HBA1C_TARGET = 7.0
CGM_MEAN_TARGET = 154.0
NO_LABEL = ["Healthy", "Pre-DM"]

ECG_METRICS = {"Rate": "rate_bpm", "PR": "pr_ms", "QRSD": "qrsd_ms",
               "QT": "qt_ms", "QTc": "qtc_ms"}


def load_full(**cutoffs) -> pd.DataFrame:
    """The Phase-2 table with every derived Phase-2 exposure attached."""
    df = _phase2.load(**cutoffs)

    # Track A — CGM metrics (build_cgm_metrics.py), as in run_e2a_1 / run_e2a_2.
    cgm_path = azure_io.repo_root() / "data" / "processed" / "p1" / "cgm_metrics.parquet"
    if cgm_path.exists():
        cgm = pd.read_parquet(cgm_path)
        cgm["person_id"] = cgm["person_id"].astype(str)
        df = df.merge(cgm[["person_id", "glucose_mean", "glucose_cv", "tar_180", "mage",
                           "pct_censored"]], on="person_id", how="left")
    else:
        for c in ("glucose_mean", "glucose_cv", "tar_180", "mage", "pct_censored"):
            df[c] = np.nan

    # Track E — ECG numeric metrics, deduplicated to the first record (run_e2e_2).
    manifest = azure_io.load_table("manifest_ecg")
    manifest["person_id"] = manifest["person_id"].astype(str)
    ecg = manifest.drop_duplicates("person_id", keep="first").rename(columns=ECG_METRICS)
    for column in ECG_METRICS.values():
        ecg[column] = pd.to_numeric(ecg[column], errors="coerce")
    df = df.merge(ecg[["person_id", *ECG_METRICS.values()]], on="person_id", how="left")

    # Track F — PhenX SDOH scores (run_e2f_1).
    obs = omop.add_item_key(azure_io.load_table(
        "observation", usecols=["person_id", "observation_source_value", "value_as_number"]))
    scores = omop.phenx_scores(obs).reset_index()
    scores["person_id"] = scores["person_id"].astype(str)
    df = df.merge(scores, on="person_id", how="left")

    # Track B — obesity flag (run_e2b_1).
    df["bmi_obese"] = df["bmi"].ge(30).astype(float).mask(df["bmi"].isna())

    # Track A — discordance flags (run_e2a_2).
    df["undiagnosed_range"] = (
        df["study_group_label"].isin(NO_LABEL) & df["hba1c"].ge(HBA1C_DIABETES)
    ).astype(float).mask(df["hba1c"].isna())
    df["undiagnosed_range_cgm"] = (
        df["study_group_label"].isin(NO_LABEL) & df["glucose_mean"].ge(CGM_MEAN_TARGET)
    ).astype(float).mask(df["glucose_mean"].isna())
    df["insulin_at_target"] = (
        df["study_group_label"].eq("Insulin") & df["hba1c"].lt(HBA1C_TARGET)
    ).astype(float).mask(df["hba1c"].isna())

    # Unrecognized on either organ, exactly as E1.2 / E2C.2 / E2F.1 define it.
    either = thresholds.either_organ(df)
    df["unrec_either"] = either["unrecognized"]
    df.loc[~(either["abnormal"] & either["answered"]), "unrec_either"] = np.nan
    return df


# ── Per-site replication ────────────────────────────────────────────────

def _drop_site(covariates: list[str]) -> list[str]:
    return [c for c in covariates if "clinical_site" not in c]


def fit_by_site(df: pd.DataFrame, outcome: str, exposure: str,
                covariates: list[str], *, family: str = "binomial",
                universe: pd.Series | None = None) -> pd.DataFrame:
    """The same model fitted within each clinical site.

    Site cannot be a covariate inside a site stratum, so it is dropped; the rest
    of the covariate set is kept as-is. Exposure scaling uses the *cohort-wide*
    SD, as `associations.fit` does, so site estimates stay on the pooled scale.
    """
    frame = df if universe is None else df[universe]
    sd = float(df[exposure].std())
    rows = []
    for site in SITES:
        sub = frame[frame["clinical_site"] == site].copy()
        # Pre-scale with the cohort-wide SD so per-site fits share the pooled
        # scale; then fit unscaled.
        binary = associations._is_binary(df[exposure])
        if not binary and sd and np.isfinite(sd):
            sub[f"{exposure}_z"] = sub[exposure] / sd
            term = f"{exposure}_z"
        else:
            term = exposure
        row = associations.fit(sub, outcome, term, _drop_site(covariates),
                               family=family, scale_by_sd=False)
        # A logistic fit that hits complete separation returns an absurd point
        # estimate with a 0-to-infinity interval and p ~ 1. That is a failed
        # fit, not evidence about direction, and must not count toward site
        # consistency.
        if family == "binomial" and pd.notna(row["estimate"]) and (
                not np.isfinite(row["ci_hi"]) or row["ci_hi"] > 1e4 or row["ci_lo"] < 1e-4
                or row["estimate"] > 1e3 or row["estimate"] < 1e-3):
            row.update({"estimate": np.nan, "ci_lo": np.nan, "ci_hi": np.nan, "p": np.nan,
                        "note": "fit unstable: separation (tiny cell)"})
        row["site"] = site
        row["exposure"] = exposure
        rows.append(row)
    out = pd.DataFrame(rows).set_index("site")
    return out[["exposure", "outcome", "n", "estimate", "ci_lo", "ci_hi", "p", "note"]]


def site_consistency(site_table: pd.DataFrame, pooled_estimate: float,
                     *, family: str = "binomial") -> dict:
    """Direction agreement across sites, plus a Cochran's Q heterogeneity test.

    "Consistent" = every site's estimate lies on the same side of the null as
    the pooled estimate. Significance within a site is reported but not
    required: three sites of ~760 are individually under-powered for most of
    what this paper tests.
    """
    null = 1.0 if family == "binomial" else 0.0
    est = site_table["estimate"].astype(float)
    ok = est.notna()
    pooled_side = np.sign(np.log(pooled_estimate) if family == "binomial" else pooled_estimate)
    if family == "binomial":
        sides = np.sign(np.log(est[ok]))
    else:
        sides = np.sign(est[ok])
    same = bool(ok.sum() == len(site_table) and (sides == pooled_side).all())

    # Heterogeneity on the log scale (binomial) or raw scale (gaussian).
    if family == "binomial":
        theta = np.log(est[ok])
        se = (np.log(site_table.loc[ok, "ci_hi"].astype(float))
              - np.log(site_table.loc[ok, "ci_lo"].astype(float))) / (2 * 1.96)
    else:
        theta = est[ok]
        se = (site_table.loc[ok, "ci_hi"].astype(float)
              - site_table.loc[ok, "ci_lo"].astype(float)) / (2 * 1.96)
    q_p, i2 = np.nan, np.nan
    if ok.sum() >= 2 and (se > 0).all():
        w = 1 / se**2
        pooled = float((w * theta).sum() / w.sum())
        q = float((w * (theta - pooled) ** 2).sum())
        dof = int(ok.sum() - 1)
        q_p = float(_sps.chi2.sf(q, dof))
        i2 = max(0.0, (q - dof) / q) * 100 if q > 0 else 0.0
    return {
        "sites_fitted": int(ok.sum()),
        "sites_same_direction": int((sides == pooled_side).sum()),
        "sites_p_lt_05": int((site_table.loc[ok, "p"].astype(float) < 0.05).sum()),
        "consistent_across_sites": same,
        "heterogeneity_q_p": q_p,
        "i_squared_pct": round(float(i2), 1) if np.isfinite(i2) else np.nan,
    }


# ── PRESPEC reader ──────────────────────────────────────────────────────

def prespec() -> dict:
    """Parameters from the machine-readable block in PRESPEC.md.

    E3.3 runs against these rather than against constants typed into the
    runner, so the frozen document and the executed analysis cannot diverge.
    """
    text = PRESPEC.read_text(encoding="utf-8")
    m = re.search(r"```json\s*\n(.*?)\n```", text, re.S)
    if not m:
        raise RuntimeError("PRESPEC.md has no ```json parameter block")
    return json.loads(m.group(1))


def prespec_sha256() -> str:
    import hashlib
    return hashlib.sha256(PRESPEC.read_bytes()).hexdigest()
