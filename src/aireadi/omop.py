"""Parsing and cleaning for the OMOP clinical tables.

Both `observation.csv` and `measurement.csv` encode the variable name in a
`*_source_value` column as ``"<item_key>, <human readable description>"``.
Everything here keys off that first field.

The one rule that matters: run every survey value through
`clean_survey_values` before it reaches an aggregation. Survey special codes
(555 / 777 / 99) are not measurements.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from .constants import (
    MEASUREMENT_KEYS,
    MHOCCUR_EXCLUDE,
    MHOCCUR_PREFIX,
    OBSERVATION_KEYS,
    OPERATOR_BELOW_DETECTION,
    PLAUSIBLE_RANGES,
    SURVEY_SPECIAL_CODES,
)

__all__ = [
    "item_key",
    "add_item_key",
    "clean_survey_values",
    "item_descriptions",
    "pivot_items",
    "first_value",
    "extract_lab",
    "comorbidity_count",
    "phenx_family",
    "phenx_scores",
]

OBSERVATION_KEY_COL = "observation_source_value"
MEASUREMENT_KEY_COL = "measurement_source_value"


def item_key(source_value: pd.Series) -> pd.Series:
    """Extract the item key from an OMOP `*_source_value` column.

    ``"cestl, CESD Total Score"`` -> ``"cestl"``. Lowercased and stripped so
    downstream comparisons never depend on source casing.
    """
    return (
        source_value.astype(str)
        .str.split(",", n=1)
        .str[0]
        .str.strip()
        .str.lower()
    )


def add_item_key(df: pd.DataFrame, *, source_col: str | None = None,
                 value_col: str = "value_as_number",
                 clean_special: bool = True) -> pd.DataFrame:
    """Return `df` with `item_key` and numeric `value_clean` columns added.

    `clean_special=True` (the default) maps survey special codes to NaN. Turn
    it off only when you specifically want to inspect the raw codes -- for
    example when auditing how often an item was refused.
    """
    if source_col is None:
        if OBSERVATION_KEY_COL in df.columns:
            source_col = OBSERVATION_KEY_COL
        elif MEASUREMENT_KEY_COL in df.columns:
            source_col = MEASUREMENT_KEY_COL
        else:
            raise KeyError(
                "No source-value column found; pass source_col explicitly."
            )

    out = df.copy()
    out["item_key"] = item_key(out[source_col])
    out["value_clean"] = pd.to_numeric(out[value_col], errors="coerce")
    if clean_special:
        out["value_clean"] = clean_survey_values(out["value_clean"])
    out["person_id"] = out["person_id"].astype(str)
    return out


def clean_survey_values(values: pd.Series,
                        codes: tuple[int, ...] = SURVEY_SPECIAL_CODES) -> pd.Series:
    """Map survey special codes to NaN.

    555 = not asked / not applicable, 777 = refused / don't know, 99 =
    sentinel. Every EDA-era notebook scrubbed only 99, which is how a
    1-6 Likert score ended up with a maximum of 777.

    Note the asymmetry this cannot resolve: 99 is a legitimate value for a
    count item (e.g. a fall count). Only call this on scale/Likert items, and
    pass a narrower `codes` tuple for count items.
    """
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric.mask(numeric.isin(codes))


def item_descriptions(df: pd.DataFrame, *, source_col: str | None = None) -> pd.Series:
    """Map item_key -> the human-readable half of the source value.

    Useful for E0.2-style mapping tables where the exact question wording
    has to be reported.
    """
    if source_col is None:
        source_col = (
            OBSERVATION_KEY_COL if OBSERVATION_KEY_COL in df.columns
            else MEASUREMENT_KEY_COL
        )
    keys = item_key(df[source_col])
    desc = (
        df[source_col].astype(str)
        .str.split(",", n=1)
        .str[1]
        .str.strip()
    )
    return (
        pd.DataFrame({"item_key": keys, "description": desc})
        .dropna()
        .drop_duplicates("item_key")
        .set_index("item_key")["description"]
        .sort_index()
    )


def pivot_items(df: pd.DataFrame, keys: list[str] | None = None, *,
                prefix: str | None = None,
                item_pattern: str | None = None,
                aggfunc: str = "first") -> pd.DataFrame:
    """Pivot long OMOP rows into one row per participant, one column per item.

    Pass an explicit `keys` list, a `prefix` (e.g. "pxfi" for the
    food-insecurity battery), or an `item_pattern` regex for cases where a bare
    prefix is ambiguous -- see `phenx_family`. Expects the output of
    `add_item_key`.
    """
    if "item_key" not in df.columns:
        raise KeyError("Call add_item_key() first.")
    if keys is None and prefix is None and item_pattern is None:
        raise ValueError("Pass keys=, prefix=, or item_pattern=.")

    sel = df
    if keys is not None:
        sel = sel[sel["item_key"].isin(keys)]
    if prefix is not None:
        sel = sel[sel["item_key"].str.startswith(prefix, na=False)]
    if item_pattern is not None:
        sel = sel[sel["item_key"].str.match(item_pattern, na=False)]

    return sel.pivot_table(
        index="person_id", columns="item_key", values="value_clean",
        aggfunc=aggfunc,
    )


def first_value(df: pd.DataFrame, key: str, *, name: str | None = None) -> pd.Series:
    """One value per participant for a single item key.

    Expects the output of `add_item_key`. Returns an empty named Series if the
    key is absent, so a missing variable degrades to all-NaN after a merge
    rather than raising deep inside a pipeline.
    """
    if "item_key" not in df.columns:
        raise KeyError("Call add_item_key() first.")
    name = name or key
    sel = df[df["item_key"] == key]
    if sel.empty:
        return pd.Series(dtype="float64", name=name, index=pd.Index([], name="person_id"))
    return sel.groupby("person_id")["value_clean"].first().rename(name)


def extract_lab(measurement: pd.DataFrame, key: str, *, name: str | None = None,
                plausible: tuple[float, float] | None = None,
                flag_below_detection: bool = False) -> pd.DataFrame:
    """Extract one lab per participant from `measurement.csv`.

    Takes the most recent value per person when a date column is present,
    after dropping physiologically implausible readings.

    `flag_below_detection=True` adds a `<name>_below_detection` boolean built
    from `operator_concept_id == 4171756`. Troponin needs this: below-detection
    rows carry a value that is a limit, not a measurement, and treating them as
    ordinary numbers makes every heart-injury count wrong.
    """
    name = name or key
    df = measurement.copy()
    df["person_id"] = df["person_id"].astype(str)
    df["mkey"] = item_key(df[MEASUREMENT_KEY_COL])
    sel = df[df["mkey"] == key].copy()
    if sel.empty:
        cols = ["person_id", name]
        if flag_below_detection:
            cols.append(f"{name}_below_detection")
        return pd.DataFrame(columns=cols)

    sel[name] = pd.to_numeric(sel["value_as_number"], errors="coerce")

    if flag_below_detection:
        op = pd.to_numeric(sel.get("operator_concept_id"), errors="coerce")
        sel[f"{name}_below_detection"] = op.eq(OPERATOR_BELOW_DETECTION).fillna(False)

    if plausible is None:
        plausible = PLAUSIBLE_RANGES.get(name)
    if plausible is not None:
        lo, hi = plausible
        # Keep below-detection rows: their value is a limit, not a reading.
        keep = sel[name].between(lo, hi)
        if flag_below_detection:
            keep = keep | sel[f"{name}_below_detection"]
        sel = sel[keep]

    if "measurement_date" in sel.columns:
        sel["measurement_date"] = pd.to_datetime(sel["measurement_date"], errors="coerce")
        sel = sel.sort_values("measurement_date")

    keep_cols = [name] + ([f"{name}_below_detection"] if flag_below_detection else [])
    return (
        sel.groupby("person_id")[keep_cols].last().reset_index()
    )


def comorbidity_count(observation_with_keys: pd.DataFrame) -> pd.Series:
    """Count distinct self-reported conditions per participant.

    Excludes `mhoccur_yn` (a gate question) and `mhoccur_fallot` (a fall
    COUNT, not a flag). Values are clipped to 1 so a count item that slipped
    through cannot inflate the tally.
    """
    if "item_key" not in observation_with_keys.columns:
        raise KeyError("Call add_item_key() first.")
    mh = observation_with_keys[
        observation_with_keys["item_key"].str.startswith(MHOCCUR_PREFIX, na=False)
    ]
    disease = mh[~mh["item_key"].isin(MHOCCUR_EXCLUDE)]
    if disease.empty:
        return pd.Series(dtype="float64", name="comorbidity_count")
    wide = disease.pivot_table(
        index="person_id", columns="item_key", values="value_clean", aggfunc="first"
    )
    return wide.clip(upper=1).sum(axis=1, skipna=True).rename("comorbidity_count")


def phenx_family(observation_with_keys: pd.DataFrame, family: str) -> pd.DataFrame:
    """Pivot one PhenX battery by its item prefix.

    Always select SDOH items by prefix. The deleted EDA notebooks built three
    "different" SDOH scores by positionally slicing one alphabetically sorted
    battery -- the slices were neither contiguous nor the instrument they were
    labelled as. Every result from that era is an artifact.

    Items are matched as ``<prefix><digit>``, not by a bare `startswith`. A
    bare prefix match is wrong twice over: `pxhi` (housing, 2 items) also
    swallows the whole `pxhic` insurance battery, and every family picks up its
    own survey-metadata fields (`pxrdcmpdat`, `pxnestartts`, ...), which are
    dates and timestamps rather than responses. Both were live in this function
    until E0.3 profiled the families and caught it.
    """
    from .constants import PHENX_FAMILIES

    prefix = PHENX_FAMILIES.get(family, family)
    return pivot_items(observation_with_keys, item_pattern=rf"^{re.escape(prefix)}\d")


def phenx_scores(observation_with_keys: pd.DataFrame) -> pd.DataFrame:
    """Score the SDOH batteries P1 uses, one column per construct.

    Selecting the right items is only half the job -- `phenx_family` already does
    that. Scoring them is where the remaining traps are, and there are three:

    **1. Two batteries are NOT monotonic in their coded values.** `pxhi1` ("What
    is your living situation today?") runs 0 = no steady place (n=15), 1 = steady
    place (n=1,943), 2 = have a place but worried about losing it (n=95). Housing
    security is therefore 1 > 2 > 0, not 0 < 1 < 2, and treating the code as a
    continuous severity score points the effect in a direction that matches
    nothing. The same applies to `pxfi1`/`pxfi2`, whose 1 level is RARER than
    their 2 level (63 vs 246) -- the giveaway that the answer order is
    never / often / sometimes rather than a graded scale. Both are handled by
    recoding to an affirmative indicator, never by summing the raw code.

    **2. Skip-gated items cannot enter a summed score.** `pxahc3` (n=256),
    `pxahc4` (n=1,788) and `pxahc6` (n=30) are only asked of some participants, so
    a sum including them scores how many questions someone was asked. Only
    full-cohort items are used.

    **3. Some items are nominal.** `pxahc5` ("what kind of place do you go to")
    and `pxhi2` (a housing-problem list where 8 = none, n=1,707) are categories,
    not quantities. They are excluded rather than summed.

    Scores returned, all oriented so HIGHER MEANS MORE HARDSHIP:

    ``food_insecurity``            USDA 5-item short-form affirmative count, 0-5
    ``food_insecure``              USDA short-form cutoff, >= 2 affirmatives
    ``prescription_unaffordable``  count of pxpa1-4, 0-4
    ``clinician_discrimination``   mean of pxdhc1-7, 1-5
    ``healthcare_access_barriers`` count of the three unambiguous barrier items
    ``housing_insecure``           pxhi1 recoded: 1 if no steady place or at risk

    See docs/CAVEATS.md, "PhenX SDOH".
    """
    out = {}

    food = phenx_family(observation_with_keys, "food_insecurity")
    # Affirmative = "often true" or "sometimes true" for the two 0-2 items, which
    # is USDA's own scoring and sidesteps their non-monotonic coding entirely.
    graded = [c for c in ("pxfi1", "pxfi2") if c in food.columns]
    binary = [c for c in ("pxfi3", "pxfi4", "pxfi5") if c in food.columns]
    parts = [food[c].isin([1, 2]).astype(float).mask(food[c].isna()) for c in graded]
    parts += [food[c].eq(1).astype(float).mask(food[c].isna()) for c in binary]
    if parts:
        affirmative = pd.concat(parts, axis=1)
        # Require most of the instrument before scoring anyone, so a participant
        # who answered one item does not get a reassuring 0.
        enough = affirmative.notna().sum(axis=1).ge(4)
        out["food_insecurity"] = affirmative.sum(axis=1, skipna=True).mask(~enough)
        out["food_insecure"] = out["food_insecurity"].ge(2).astype(float).mask(~enough)

    presc = phenx_family(observation_with_keys, "prescription_affordability")
    cols = [c for c in ("pxpa1", "pxpa2", "pxpa3", "pxpa4") if c in presc.columns]
    if cols:
        enough = presc[cols].notna().sum(axis=1).ge(3)
        out["prescription_unaffordable"] = (
            presc[cols].eq(1).sum(axis=1).astype(float).mask(~enough))

    disc = phenx_family(observation_with_keys, "clinician_discrimination")
    cols = [c for c in disc.columns if re.fullmatch(r"pxdhc[1-7]", c)]
    if cols:
        enough = disc[cols].notna().sum(axis=1).ge(5)
        out["clinician_discrimination"] = disc[cols].mean(axis=1).mask(~enough)

    access = phenx_family(observation_with_keys, "healthcare_access")
    # Only the three unambiguous, full-cohort, same-direction barrier items.
    cols = [c for c in ("pxahc8", "pxahc9", "pxahc10") if c in access.columns]
    if cols:
        enough = access[cols].notna().sum(axis=1).ge(2)
        out["healthcare_access_barriers"] = (
            access[cols].eq(1).sum(axis=1).astype(float).mask(~enough))

    housing = phenx_family(observation_with_keys, "housing_insecurity")
    if "pxhi1" in housing.columns:
        out["housing_insecure"] = (
            housing["pxhi1"].isin([0, 2]).astype(float).mask(housing["pxhi1"].isna()))

    return pd.DataFrame(out)
