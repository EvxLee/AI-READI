"""Tests for the Phase-1 layer: abnormality flags and the sweep statistics.

Offline. The statistics are cross-checked against independent implementations
(statsmodels) rather than against numbers this repo produced, so a shared
misunderstanding cannot pass.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aireadi import stats, thresholds


# ── Wilson intervals ────────────────────────────────────────────────────

@pytest.mark.parametrize("k,n", [(0, 10), (1, 10), (5, 10), (10, 10),
                                 (89, 315), (226, 315), (3, 258)])
def test_wilson_matches_statsmodels(k, n):
    sm = pytest.importorskip("statsmodels.stats.proportion")
    want = sm.proportion_confint(k, n, alpha=0.05, method="wilson")
    got = stats.wilson_ci(k, n)
    assert got == pytest.approx(want, abs=1e-10)


def test_wilson_stays_inside_the_unit_interval():
    """The normal approximation runs off the end here; Wilson must not."""
    lo, hi = stats.wilson_ci(0, 20)
    assert lo == 0.0 and 0 < hi < 1
    lo, hi = stats.wilson_ci(20, 20)
    assert hi == 1.0 and 0 < lo < 1


def test_empty_cell_does_not_raise():
    assert all(np.isnan(v) for v in stats.wilson_ci(0, 0))


# ── Trend ───────────────────────────────────────────────────────────────

def test_cochran_armitage_matches_linear_by_linear():
    """CA trend equals the linear-by-linear association test, up to N vs N-1.

    statsmodels' `test_ordinal_association` is an independent implementation of
    the same statistic, but it scales the variance by N-1 where the classic
    Cochran-Armitage uses N. The two therefore differ by exactly
    sqrt(N / (N-1)) -- pinned here rather than papered over with a loose
    tolerance, so a real error in the formula cannot hide inside the slack.
    """
    ct = pytest.importorskip("statsmodels.stats.contingency_tables")
    successes, totals = [66, 57, 120, 76], [765, 550, 662, 248]
    z, _ = stats.cochran_armitage(successes, totals)

    table = np.array([[k, n - k] for k, n in zip(successes, totals)])
    ref = ct.Table(table).test_ordinal_association(
        row_scores=np.arange(4), col_scores=np.array([1, 0])
    )
    n_total = sum(totals)
    assert abs(z) == pytest.approx(
        abs(ref.zscore) * np.sqrt(n_total / (n_total - 1)), rel=1e-12
    )


def test_trend_direction_has_the_expected_sign():
    rising = stats.cochran_armitage([5, 10, 20, 40], [100] * 4)[0]
    falling = stats.cochran_armitage([40, 20, 10, 5], [100] * 4)[0]
    assert rising > 0 > falling


def test_degenerate_trend_returns_nan_not_a_crash():
    assert np.isnan(stats.cochran_armitage([0, 0, 0], [10, 10, 10])[0])
    assert np.isnan(stats.cochran_armitage([10, 10, 10], [10, 10, 10])[0])


# ── Proportion tables ───────────────────────────────────────────────────

def _toy():
    return pd.DataFrame({
        "study_group_label": pd.Categorical(
            ["Healthy"] * 4 + ["Pre-DM"] * 4 + ["Oral Med"] * 4 + ["Insulin"] * 4,
            categories=["Healthy", "Pre-DM", "Oral Med", "Insulin"], ordered=True),
        "flag": [0, 0, 0, 0] + [0, 0, 0, 1] + [0, 0, 1, 1] + [0, 1, 1, np.nan],
    })


def test_missing_is_excluded_from_the_denominator_not_counted_as_negative():
    out = stats.proportion_by_group(_toy(), "flag")
    assert out.loc["Insulin", "n"] == 3      # not 4
    assert out.loc["Insulin", "k"] == 2
    assert out.loc["Overall", "n"] == 15     # not 16


def test_group_rows_keep_the_ordered_severity_sequence():
    out = stats.proportion_by_group(_toy(), "flag")
    assert list(out.index) == ["Overall", "Healthy", "Pre-DM", "Oral Med", "Insulin"]


def test_group_counts_sum_to_the_overall_row():
    out = stats.proportion_by_group(_toy(), "flag")
    groups = out.drop(index="Overall")
    assert groups["n"].sum() == out.loc["Overall", "n"]
    assert groups["k"].sum() == out.loc["Overall", "k"]


# ── Damage flags ────────────────────────────────────────────────────────

def _master():
    """Six participants covering every branch that matters."""
    return pd.DataFrame({
        "person_id": list("abcdef"),
        #        a      b      c      d       e      f
        "acr_mg_g":        [7.0,  45.0,  30.0,  np.nan, 500.0, 12.0],
        "troponin_t":      [6.0,  20.0,  14.0,  9.0,    np.nan, 6.0],
        "troponin_t_below_detection": [True, False, False, False, False, True],
        "monofilament_min": [10.0, 8.0,   9.0,   0.0,    10.0,  np.nan],
        "sr_kidney":       [0.0,  0.0,   1.0,   0.0,    np.nan, 0.0],
        "sr_heart":        [0.0,  0.0,   0.0,   1.0,    0.0,   np.nan],
    })


def test_unmeasured_marker_stays_missing_and_never_becomes_normal():
    out = thresholds.add_damage_flags(_master())
    assert pd.isna(out.loc[3, "abn_kidney"])   # d: no ACR
    assert pd.isna(out.loc[4, "abn_heart"])    # e: no troponin
    assert pd.isna(out.loc[5, "abn_nerve"])    # f: no monofilament


def test_cutoffs_are_inclusive_at_the_boundary():
    out = thresholds.add_damage_flags(_master())
    assert out.loc[2, "abn_kidney"] == 1.0     # ACR exactly 30
    assert out.loc[2, "abn_heart"] == 1.0      # troponin exactly 14
    assert out.loc[1, "abn_nerve"] == 1.0      # 2 missed sites exactly
    assert out.loc[2, "abn_nerve"] == 0.0      # 1 missed site

def test_detectable_rung_uses_the_operator_not_the_reported_value():
    """712 people carry a troponin reported AT the 6 ng/L limit.

    Those are limits, not readings: `>= 6` would call every one of them
    abnormal. The 'detectable' rung must key off the below-detection operator.
    """
    out = thresholds.add_damage_flags(_master(), troponin_ng_l="detectable")
    assert out.loc[0, "abn_heart"] == 0.0      # value 6.0, flagged below LOD
    assert out.loc[3, "abn_heart"] == 1.0      # value 9.0, a real reading
    naive = _master()["troponin_t"].ge(6.0)
    assert bool(naive.iloc[0]) and out.loc[0, "abn_heart"] == 0.0


def test_unrecognized_is_defined_only_among_the_abnormal_with_an_answer():
    out = thresholds.add_damage_flags(_master())
    assert out.loc[1, "unrec_kidney"] == 1.0   # abnormal, said no
    assert out.loc[2, "unrec_kidney"] == 0.0   # abnormal, said yes
    assert pd.isna(out.loc[0, "unrec_kidney"])  # normal -> not in the denominator
    assert pd.isna(out.loc[4, "unrec_kidney"])  # abnormal but refused the item


def test_nerve_never_gets_an_unrecognized_flag():
    """E0.GATE: no neuropathy self-report item exists in v3.0.0."""
    out = thresholds.add_damage_flags(_master())
    assert "unrec_nerve" not in out.columns
    assert thresholds.UNRECOGNIZED_ORGANS == ["kidney", "heart"]


def test_organ_counts_require_every_contributing_organ_to_be_evaluable():
    out = thresholds.add_damage_flags(_master())
    assert out.loc[0, "n_organs_abnormal"] == 0.0
    assert out.loc[1, "n_organs_abnormal"] == 3.0
    assert pd.isna(out.loc[3, "n_organs_abnormal"])   # d has no ACR
    # e is abnormal on kidney but refused the kidney item -> not countable
    assert pd.isna(out.loc[4, "n_organs_unrecognized"])
    assert out.loc[1, "n_organs_unrecognized"] == 2.0


def test_sweep_grid_contains_the_primary_value():
    for k, v in thresholds.PRIMARY.items():
        assert v in thresholds.SWEEP[k], k


def test_bad_troponin_rung_is_rejected_loudly():
    with pytest.raises(ValueError, match="detectable"):
        thresholds.add_damage_flags(_master(), troponin_ng_l="elevated")
