"""E3.1 — Rank everything in the log on the plan's four criteria.

The plan (Part II, Phase 3) says: rank every finding on effect size, survival
of age + severity + site adjustment, consistency across the three sites, and
coherence with the core story — and that a p-value alone does not qualify a
finding. This runner does exactly that for every model in every Phase-2
primary family (207 associations) plus the Phase-1 core claims, so `E3.2` can
pick the headline set from a table rather than from memory.

Three of the four criteria are mechanical and are computed here:

* **Effect size** — a per-SD odds ratio of at least 1.2 (either direction), a
  yes/no odds ratio of at least 1.5, or a standardised linear coefficient of
  at least 0.10 SD per SD of exposure (0.20 SD for a yes/no exposure, the
  linear counterpart of OR 1.5). For the Phase-1 trend claims, at least a
  10-point spread between Healthy and Insulin, computed from the counts, not
  from rounded percentages. These are floors for "worth a sentence", not
  claims about clinical importance. Within a tier, rows are ordered by how far
  the effect sits above its own floor, then by q — so a strong yes/no odds
  ratio is not buried beneath a dozen small per-SD ones with tinier q.
* **Survives adjustment** — q < 0.05 within the experiment's primary adjusted
  family, read from the committed artifact.
* **Consistent across sites** — the model refitted within UW, UAB and UCSD
  separately, with every site estimate on the same side of the null as the
  pooled one. Per-site significance is reported, not required.

The fourth, **coherence with the core story**, is a judgement — so it is coded
from a fixed rubric written down here rather than assigned row by row:
pre-declared hypotheses (H1 core sweep, H2 CES-D vs damage, H3 CES-D vs
unrecognized) and findings that speak directly to Aim 1 (undiagnosed-range
glycaemia, ECG corroboration of the heart marker, access barriers as a
mechanism for being unrecognized, and measured glycaemia tracking damage
beyond the treatment label — expected biology that corroborates the severity
gradient) count as coherent; tracks that carried no hypothesis (BMI,
wearables, PAID-5) do not, however strong their signal. Coherent is a filter
for the E3.2 shortlist, not a promotion: E2A.1 passes it and is still set
aside for the headline in PRESPEC.md §9, because the paper is about
recognition and its glycaemia result is textbook.

`E2.AGE` established that a crude estimate in this cohort is not a conservative
version of the adjusted one, so nothing here ranks on unadjusted numbers.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from aireadi import associations, figures, results, stats, thresholds

import _phase3

_phase3.banner("E3.1", "Rank every finding on the four plan criteria")

df = _phase3.load_full()
R = _phase3.RESULTS

# ── Effect-size floors ──────────────────────────────────────────────────
OR_PER_SD_FLOOR = 1.2
OR_BINARY_FLOOR = 1.5
BETA_SD_FLOOR = 0.10          # per-SD exposure on a continuous outcome
BETA_SD_BINARY_FLOOR = 0.20   # yes/no exposure on a continuous outcome (~ OR 1.5)
TREND_SPREAD_FLOOR = 10.0     # percentage points, Insulin minus Healthy


def effect_ok(estimate: float, scale: str, family: str, outcome_sd: float) -> tuple[float, bool, float]:
    """Standardised effect size, whether it clears its floor, and the margin over the floor.

    The margin (size / floor, on the log-odds scale for odds ratios) is the one
    quantity comparable across a per-SD odds ratio, a yes/no odds ratio and a
    standardised linear coefficient, so it is what the within-tier sort uses.
    """
    if pd.isna(estimate):
        return np.nan, False, np.nan
    if family == "binomial":
        size = abs(np.log(estimate))
        floor = np.log(OR_BINARY_FLOOR if scale == "yes vs no" else OR_PER_SD_FLOOR)
        return round(float(np.exp(size)), 3), bool(size >= floor), round(float(size / floor), 3)
    size = abs(estimate) / outcome_sd if outcome_sd else np.nan
    floor = BETA_SD_BINARY_FLOOR if scale == "yes vs no" else BETA_SD_FLOOR
    return round(float(size), 3), bool(size >= floor), round(float(size / floor), 3)


# ── Coherence rubric ────────────────────────────────────────────────────
def coherence(experiment: str, exposure: str, outcome: str) -> tuple[str, bool]:
    if experiment.startswith("E1."):
        return "pre-declared — H1 core sweep", True
    if experiment == "E2C.1":
        return "pre-declared — H2 (Aim 2)", True
    if experiment == "E2C.2":
        return "pre-declared — H3", True
    if experiment == "E2A.2":
        if exposure.startswith("undiagnosed_range"):
            return "core-adjacent — unrecognized diabetes beneath unrecognized damage", True
        return "exploratory — no committed hypothesis", False
    if experiment == "E2E.2":
        if outcome in ("abn_heart", "log_troponin"):
            return "corroborative — independent instrument agrees with the heart marker", True
        return "exploratory — no committed hypothesis", False
    if experiment == "E2A.1":
        return "corroborative — measured glycaemia tracks damage beyond the label", True
    if experiment == "E2F.1":
        return "mechanistic — tests why damage goes unrecognized", True
    return "exploratory — no committed hypothesis", False


# ── Candidate universe: every primary-family model in Phase 2 ──────────
SOURCES = [
    # (experiment, artifact, primary adjustment label, covariates used, universe column)
    ("E2C.1", "E2C_1_sweep.csv", "damage", associations.ADJUSTMENTS["damage"], None),
    ("E2C.3", "E2C_3_sweep.csv", "damage", associations.ADJUSTMENTS["damage"], None),
    ("E2A.1", "E2A_1_sweep.csv", "damage", associations.ADJUSTMENTS["damage"], None),
    ("E2B.1", "E2B_1_sweep.csv", "damage", associations.ADJUSTMENTS["damage"], None),
    ("E2D.1", "E2D_1_sweep.csv", "damage", associations.ADJUSTMENTS["damage"], None),
    ("E2E.2", "E2E_2_sweep.csv", "damage", associations.ADJUSTMENTS["damage"], None),
]
MARKER = {"unrec_kidney": ["log_acr"], "unrec_heart": ["log_troponin"],
          "unrec_either": ["log_acr", "log_troponin"]}

candidates = []
for experiment, artifact, adjustment, covariates, _ in SOURCES:
    t = pd.read_csv(R / artifact)
    t = t[t["adjustment"] == adjustment]
    for r in t.itertuples(index=False):
        candidates.append({
            "experiment": experiment, "exposure": r.exposure, "outcome": r.outcome,
            "exposure_label": r.exposure_label, "outcome_label": r.outcome_label,
            "family": r.family, "scale": r.scale, "n": r.n,
            "estimate": r.estimate, "ci_lo": r.ci_lo, "ci_hi": r.ci_hi,
            "p": r.p, "q": r.q, "covariates": covariates, "universe": None,
        })

# E2F.1 and E2C.2: recognition families with marker magnitude.
for experiment, artifact, adjustment in [("E2F.1", "E2F_1_models.csv", "full"),
                                         ("E2C.2", "E2C_2.csv", "recognition+marker")]:
    t = pd.read_csv(R / artifact)
    t = t[t["adjustment"] == adjustment]
    for r in t.itertuples(index=False):
        candidates.append({
            "experiment": experiment, "exposure": r.exposure, "outcome": r.outcome,
            "exposure_label": r.exposure_label, "outcome_label": r.outcome_label,
            "family": "binomial", "scale": r.scale, "n": r.n,
            "estimate": r.estimate, "ci_lo": r.ci_lo, "ci_hi": r.ci_hi,
            "p": r.p, "q": r.q,
            "covariates": associations.ADJUSTMENTS["recognition"] + MARKER[r.outcome],
            "universe": None,
        })

# E2A.2: age + site within a universe; the exposure is yes/no.
t = pd.read_csv(R / "E2A_2_models.csv")
UNIVERSE = {"undiagnosed_range": df["study_group_label"].isin(_phase3.NO_LABEL),
            "undiagnosed_range_cgm": df["study_group_label"].isin(_phase3.NO_LABEL),
            "insulin_at_target": df["study_group_label"].eq("Insulin")}
for r in t.itertuples(index=False):
    candidates.append({
        "experiment": "E2A.2", "exposure": r.definition, "outcome": r.outcome,
        "exposure_label": r.definition, "outcome_label": associations.BINARY_OUTCOMES[r.outcome],
        "family": "binomial", "scale": r.scale, "n": r.n,
        "estimate": r.estimate, "ci_lo": r.ci_lo, "ci_hi": r.ci_hi,
        "p": r.p, "q": r.q, "covariates": ["age", "C(clinical_site)"],
        "universe": r.definition,
    })

print(f"Phase-2 candidate associations: {len(candidates)}")

# ── Score every Phase-2 candidate, with per-site refits ─────────────────
rank_rows, site_rows = [], []
for i, c in enumerate(candidates):
    fam = c["family"]
    outcome_sd = float(df[c["outcome"]].std()) if fam == "gaussian" else np.nan
    size, effect, margin = effect_ok(c["estimate"], c["scale"], fam, outcome_sd)
    survives = bool(pd.notna(c["q"]) and c["q"] < 0.05)

    universe = UNIVERSE[c["universe"]] if c["universe"] else None
    by_site = _phase3.fit_by_site(df, c["outcome"], c["exposure"], c["covariates"],
                                  family=fam, universe=universe)
    consistency = _phase3.site_consistency(by_site, c["estimate"], family=fam)
    for site, s in by_site.iterrows():
        site_rows.append({"experiment": c["experiment"], "exposure": c["exposure"],
                          "outcome": c["outcome"], "site": site, "n": s.n,
                          "estimate": s.estimate, "ci_lo": s.ci_lo, "ci_hi": s.ci_hi,
                          "p": s.p, "note": s.note})

    tier, coherent = coherence(c["experiment"], c["exposure"], c["outcome"])
    criteria = int(effect) + int(survives) + int(consistency["consistent_across_sites"]) + int(coherent)
    rank_rows.append({
        "experiment": c["experiment"], "exposure": c["exposure"], "outcome": c["outcome"],
        "exposure_label": c["exposure_label"], "outcome_label": c["outcome_label"],
        "scale": c["scale"], "family": fam, "n": c["n"],
        "estimate": c["estimate"], "ci_lo": c["ci_lo"], "ci_hi": c["ci_hi"],
        "p": c["p"], "q": c["q"],
        "effect_size_standardised": size, "effect_margin_over_floor": margin,
        "crit_effect_size": effect,
        "crit_survives_adjustment": survives,
        **consistency,
        "crit_consistent_sites": consistency["consistent_across_sites"],
        "coherence_tier": tier, "crit_coherent_with_core": coherent,
        "criteria_met": criteria,
    })
    if (i + 1) % 25 == 0:
        print(f"  scored {i + 1}/{len(candidates)}")

ranking = pd.DataFrame(rank_rows)
ranking = ranking.sort_values(["criteria_met", "effect_margin_over_floor", "q"],
                              ascending=[False, False, True])
ranking.insert(0, "rank", np.arange(1, len(ranking) + 1))
ranking = ranking.set_index("rank")
site_table = pd.DataFrame(site_rows).set_index(["experiment", "exposure", "outcome", "site"])

# ── The Phase-1 core claims, scored on the same four criteria ───────────
# Effect size = Insulin-minus-Healthy spread; adjustment = the E1.4 model
# result (kidney survives, heart attenuates — read from the artifact) for the
# recognition claims and the trend p for prevalence; site consistency = the
# trend has the same sign inside every site.
core_rows, core_site_rows = [], []


def trend_by_site(flag: pd.Series, label: str) -> tuple[bool, list[dict]]:
    pooled = stats.proportion_by_group(df.assign(_x=flag), "_x")
    pooled_sign = np.sign(float(pooled.loc["Overall", "trend_z"]))
    signs, rows = [], []
    for site in _phase3.SITES:
        sub = df[df["clinical_site"] == site].assign(_x=flag[df["clinical_site"] == site])
        tab = stats.proportion_by_group(sub, "_x")
        z = float(tab.loc["Overall", "trend_z"]); p = float(tab.loc["Overall", "trend_p"])
        signs.append(np.sign(z))
        rows.append({"claim": label, "site": site, "n": int(tab.loc["Overall", "n"]),
                     "k": int(tab.loc["Overall", "k"]), "pct": float(tab.loc["Overall", "pct"]),
                     "pct_Healthy": float(tab.loc["Healthy", "pct"]),
                     "pct_Insulin": float(tab.loc["Insulin", "pct"]),
                     "trend_z": round(z, 3), "trend_p": p})
    return bool(all(s == pooled_sign for s in signs)), rows


e14 = pd.read_csv(R / "E1_4_models.csv").set_index(["organ", "model", "term"])
either = thresholds.either_organ(df)

core_claims = [
    ("E1.1", "kidney prevalence rises with severity", df["abn_kidney"], None),
    ("E1.1", "heart prevalence rises with severity", df["abn_heart"], None),
    ("E1.1", "nerve prevalence rises with severity", df["abn_nerve"], None),
    ("E1.1", "any-organ prevalence rises with severity", df["abn_any"], None),
    ("E1.2", "kidney unrecognized fraction falls with severity", df["unrec_kidney"], "kidney"),
    ("E1.2", "heart unrecognized fraction falls with severity", df["unrec_heart"], "heart"),
    ("E1.2", "either-organ unrecognized fraction falls with severity", df["unrec_either"], None),
    ("E1.2", "kidney unrecognized burden rises with severity",
     (df["abn_kidney"].eq(1) & df["sr_kidney"].eq(0)).astype(float).mask(df["abn_kidney"].isna() | df["sr_kidney"].isna()), None),
    ("E1.2", "heart unrecognized burden rises with severity",
     (df["abn_heart"].eq(1) & df["sr_heart"].eq(0)).astype(float).mask(df["abn_heart"].isna() | df["sr_heart"].isna()), None),
    ("E1.2", "either-organ unrecognized burden rises with severity",
     either["unrecognized"].where(either["answered"]), None),
    ("E1.3", "two-or-more organs rises with severity", df["abn_multi"], None),
]
for experiment, label, flag, organ in core_claims:
    pooled = stats.proportion_by_group(df.assign(_x=flag), "_x")
    spread = float(pooled.loc["Insulin", "pct"] - pooled.loc["Healthy", "pct"])
    # From the counts, not the rounded percentages: 17.4 - 7.4 is 9.999... in
    # floating point and would fail a >= 10 test that 43/247 - 56/759 passes.
    spread_raw = 100 * (pooled.loc["Insulin", "k"] / pooled.loc["Insulin", "n"]
                        - pooled.loc["Healthy", "k"] / pooled.loc["Healthy", "n"])
    consistent, rows = trend_by_site(flag, label)
    core_site_rows.extend(rows)
    # "Survives adjustment": the plan's criterion is age + severity + site, so
    # every claim gets the same adjusted model — logistic, the flag against an
    # ordinal severity score (0-3) with age and site — and the criterion is the
    # severity-score term. Nothing here ranks on the crude trend p. For the two
    # recognition claims the E1.4 model A (the plan's set) and model C (+ HbA1c,
    # BMI, marker magnitude) Insulin-vs-Healthy terms are carried alongside.
    adj = associations.fit(df.assign(_x=flag, _sev=df["study_group_code"].astype(float)),
                           "_x", "_sev", ["age", "C(clinical_site)"], scale_by_sd=False)
    survives = bool(pd.notna(adj["p"]) and adj["p"] < 0.05)
    adj_note = (f"logistic: flag ~ severity score + age + site; severity OR per step "
                f"{adj['estimate']} ({adj['ci_lo']}-{adj['ci_hi']}), p={adj['p']:.3g}")
    e14_a = e14_c = np.nan
    if organ:
        e14_a = float(e14.loc[(organ, "A: age + severity + site", "C(study_group_label)[T.Insulin]"), "p"])
        e14_c = float(e14.loc[(organ, "C: B + marker magnitude", "C(study_group_label)[T.Insulin]"), "p"])
    core_rows.append({
        "experiment": experiment, "claim": label,
        "pct_Healthy": float(pooled.loc["Healthy", "pct"]),
        "pct_Insulin": float(pooled.loc["Insulin", "pct"]),
        "spread_points": round(float(spread_raw), 2),
        "trend_z": float(pooled.loc["Overall", "trend_z"]),
        "trend_p": float(pooled.loc["Overall", "trend_p"]),
        "crit_effect_size": abs(spread_raw) >= TREND_SPREAD_FLOOR,
        "adjusted_severity_or_per_step": adj["estimate"], "adjusted_severity_p": adj["p"],
        "crit_survives_adjustment": survives, "adjustment_basis": adj_note,
        "e14_model_A_insulin_p": e14_a, "e14_model_C_insulin_p": e14_c,
        "sites_same_direction": sum(1 for r in rows if np.sign(r["trend_z"]) == np.sign(float(pooled.loc["Overall", "trend_z"]))),
        "sites_p_lt_05": sum(1 for r in rows if r["trend_p"] < 0.05),
        "crit_consistent_sites": consistent,
        "coherence_tier": "pre-declared — H1 core sweep", "crit_coherent_with_core": True,
    })
core = pd.DataFrame(core_rows)
core["criteria_met"] = core[["crit_effect_size", "crit_survives_adjustment",
                             "crit_consistent_sites", "crit_coherent_with_core"]].sum(axis=1)
core = core.set_index(["experiment", "claim"])
core_sites = pd.DataFrame(core_site_rows).set_index(["claim", "site"])

# ── Print ───────────────────────────────────────────────────────────────
pd.set_option("display.width", 250)
show = ranking[["experiment", "exposure", "outcome", "estimate", "q", "effect_size_standardised",
                "crit_effect_size", "crit_survives_adjustment", "sites_same_direction",
                "sites_p_lt_05", "crit_consistent_sites", "crit_coherent_with_core",
                "criteria_met"]]
_phase3.print_table(show.head(40), title="Top 40 Phase-2 associations by criteria met")
_phase3.print_table(core[["spread_points", "trend_z", "crit_effect_size", "adjusted_severity_or_per_step",
                          "adjusted_severity_p", "crit_survives_adjustment", "sites_same_direction",
                          "sites_p_lt_05", "crit_consistent_sites", "criteria_met"]],
                    title="Phase-1 core claims on the same four criteria")

all_four = ranking[ranking["criteria_met"] == 4]
survivors = ranking[ranking["crit_survives_adjustment"]]
print(f"\n{len(ranking)} Phase-2 associations scored; {len(survivors)} survive FDR; "
      f"{int(survivors.crit_consistent_sites.sum())} of those replicate in direction at all "
      f"three sites; {len(all_four)} meet all four criteria.")
print(f"Core claims meeting all four: {int((core.criteria_met == 4).sum())} of {len(core)}")

# ── Figure: site replication for the strongest candidates ───────────────
figures.style()
# One row per (experiment, exposure family): the best-ranked binomial row meeting all
# four criteria for each, so the figure shows the shortlist E3.2 chooses from rather
# than ten near-identical glycaemia rows. The pre-declared Aim-2 rows and the E2F.1
# negative are always shown, whatever their rank.
ALWAYS = [("E2C.1", "cesd_total", "abn_nerve"), ("E2C.1", "cesd_positive", "abn_nerve"),
          ("E2A.2", "undiagnosed_range", "abn_kidney"),
          ("E2F.1", "healthcare_access_barriers", "unrec_heart")]
four = ranking[(ranking.criteria_met == 4) & (ranking.family == "binomial")]
best = four.drop_duplicates(subset=["experiment"], keep="first")
keys = {tuple(x) for x in best[["experiment", "exposure", "outcome"]].values} | set(ALWAYS)
top = ranking[ranking.apply(lambda r: (r.experiment, r.exposure, r.outcome) in keys, axis=1)]
top = top[top.family == "binomial"].sort_values("rank" if "rank" in top.columns else "q")
if len(top):
    fig, ax = figures.new_figure(10, 0.42 * len(top) * 4 + 1.8)
    labels, ests, lo, hi, colors, sig = [], [], [], [], [], []
    palette = {"pooled": figures.INK, "UW": figures.SEVERITY[1], "UAB": figures.SEVERITY[2],
               "UCSD": figures.SEVERITY[3]}
    for r in top.itertuples():
        labels.append(f"{r.experiment} {r.exposure_label} → {r.outcome_label}  [pooled]")
        ests.append(r.estimate); lo.append(r.ci_lo); hi.append(r.ci_hi)
        colors.append(palette["pooled"]); sig.append(r.q < 0.05)
        for site in _phase3.SITES:
            s = site_table.loc[(r.experiment, r.exposure, r.outcome, site)]
            labels.append(f"      {site}")
            ests.append(s.estimate); lo.append(s.ci_lo); hi.append(s.ci_hi)
            colors.append(palette[site]); sig.append(bool(s.p < 0.05))
    figures.forest(ax, labels, ests, lo, hi, colors=colors, significant=sig)
    ax.set_xlabel("Odds ratio (per SD, or yes vs no) — filled marker: interval excludes 1")
    figures.finish(fig, "E3.1 — do the candidate findings replicate at each site?",
                   "Pooled estimate then UW / UAB / UCSD, each fitted within site with the same "
                   "covariates. One best-ranked row per experiment meeting all four criteria, "
                   "plus the pre-declared Aim-2 rows and the E2F.1 negative.",
                   source="Source: results/E3_1_ranking.csv, results/E3_1_site_replication.csv")
else:
    fig = None

# ── Save ────────────────────────────────────────────────────────────────
top_line = "; ".join(
    f"{r.experiment} {r.exposure}->{r.outcome} {r.estimate} (q={r.q:.2g}, sites {r.sites_same_direction}/3 same direction)"
    for r in all_four.head(12).itertuples())

results.save(
    "E3.1", ranking, paper="p1",
    method=("Every model in every Phase-2 primary adjusted family (E2C.1, E2C.2, E2C.3, E2A.1, "
            "E2A.2, E2B.1, E2D.1, E2E.2, E2F.1) scored on the plan's four criteria: effect "
            "size (per-SD OR >= 1.2, yes/no OR >= 1.5, or standardised beta >= 0.10 SD), "
            "survival of adjustment (q < 0.05 in the primary family), consistency across the "
            "three sites (refitted within UW, UAB and UCSD with the same covariates; every "
            "site on the pooled side of the null), and coherence with the core story (fixed "
            "rubric: pre-declared hypotheses and Aim-1-adjacent findings count, tracks with no "
            "committed hypothesis do not). Ranked by criteria met, then by the effect's margin over its "
            "floor, then q. SECOND RUN of the night: the first run counted three separation-unstable "
            "site fits as valid, tripped the spread floor on rounded percentages, scored the "
            "descriptive core claims on the crude trend p, and ordered tiers by q alone; all four "
            "were caught by the adversarial review and fixed before anything was read from it."),
    result=(f"{len(ranking)} Phase-2 associations scored; {len(survivors)} survive FDR; "
            f"{int(survivors.crit_consistent_sites.sum())} of those replicate in direction at all "
            f"three sites; {len(all_four)} meet all four criteria. Top: {top_line}."),
    decision="keep — feeds E3.2", name="ranking",
)
results.save(
    "E3.1", site_table, paper="p1",
    method="Per-site refit of every scored Phase-2 association (site dropped as a covariate).",
    result=(f"{len(site_table)} site-level fits ({len(candidates)} associations x 3 sites); "
            f"{int(site_table.note.astype(str).str.contains('fit', na=False).sum())} did not yield a "
            f"usable fit (separation in tiny cells), recorded as NaN with a note and excluded from "
            f"direction counting."),
    decision="keep", name="site_replication", primary=False,
)
results.save(
    "E3.1", core, paper="p1",
    method=("The Phase-1 core claims (prevalence, unrecognized fraction, burden, multi-organ "
            "trends) on the same four criteria: effect size = Insulin-minus-Healthy spread >= 10 "
            "points from the counts; adjustment = a logistic model of the flag on an ordinal "
            "severity score + age + site (the E1.4 model A and C Insulin terms carried alongside "
            "for the two recognition claims); site consistency = the trend keeps its sign inside "
            "every site."),
    result=("; ".join(f"{c}: spread {r.spread_points} pts, sites same-direction "
                      f"{r.sites_same_direction}/3, criteria {r.criteria_met}/4"
                      for (_, c), r in core.iterrows())),
    decision="keep", name="core_claims", primary=False,
)
results.save(
    "E3.1", core_sites, paper="p1",
    method="Per-site prevalence / unrecognized / burden trends behind the core-claim scoring.",
    result="; ".join(f"{c}@{s}: z={r.trend_z}" for (c, s), r in core_sites.iterrows()),
    decision="keep", name="core_claims_by_site", primary=False,
)
if fig is not None:
    results.save("E3.1", fig, paper="p1",
                 method="Forest of pooled and per-site estimates for the associations meeting all four criteria.",
                 result="Figure written; numbers in E3_1_ranking.csv and E3_1_site_replication.csv.",
                 decision="keep", name="figure", primary=False)
