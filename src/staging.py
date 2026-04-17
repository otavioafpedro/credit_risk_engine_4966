from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


DEFAULT_STAGE2_FLAG_COLUMNS: tuple[str, ...] = ("watchlist_flag",)
DEFAULT_STAGE3_FLAG_COLUMNS: tuple[str, ...] = (
    "problem_asset_flag",
    "restructured_flag",
    "financial_distress_flag",
)


def assign_stage(
    df: pd.DataFrame,
    pd_12m: np.ndarray | pd.Series,
    stage2_pd_relative_multiplier: float = 2.0,
    stage2_pd_absolute_increase: float = 0.05,
    stage2_dpd_threshold: int = 30,
    stage3_dpd_threshold: int = 90,
    origination_pd_column: str = "true_pd_12m",
    stage2_flag_columns: Sequence[str] = DEFAULT_STAGE2_FLAG_COLUMNS,
    stage3_flag_columns: Sequence[str] = DEFAULT_STAGE3_FLAG_COLUMNS,
) -> pd.Series:
    """Assigns Stage 1, 2 or 3 using only information observable at measurement date.

    The function intentionally ignores ``default_12m`` because that field is a future
    outcome label used for model training and validation, not for operational staging.

    Stage 2 is triggered by signs of significant increase in credit risk (SICR):
    days past due, watchlist indicators, or a material increase in PD that is both
    relatively and absolutely meaningful versus origination.

    Stage 3 is triggered by observable default or credit-impaired evidence at the
    measurement date, such as severe delinquency or explicit distress flags.
    """

    current_pd = pd.Series(pd_12m, index=df.index, dtype=float).clip(lower=0.0, upper=0.999999)
    origination_pd = _get_origination_pd(df, origination_pd_column)

    pd_ratio = current_pd / origination_pd
    pd_absolute_increase = current_pd - origination_pd

    stage2_flag_trigger = _combine_flag_columns(df, stage2_flag_columns)
    stage3_flag_trigger = _combine_flag_columns(df, stage3_flag_columns)

    sicr_trigger = (
        (pd_ratio >= stage2_pd_relative_multiplier)
        & (pd_absolute_increase >= stage2_pd_absolute_increase)
    )
    stage2_trigger = (df["dpd"] >= stage2_dpd_threshold) | stage2_flag_trigger | sicr_trigger
    stage3_trigger = (df["dpd"] >= stage3_dpd_threshold) | stage3_flag_trigger

    stage = pd.Series(1, index=df.index, dtype=int)
    stage.loc[stage2_trigger] = 2
    stage.loc[stage3_trigger] = 3
    return stage


def _get_origination_pd(df: pd.DataFrame, origination_pd_column: str) -> pd.Series:
    """Returns the origination PD series used as the SICR benchmark."""

    if origination_pd_column not in df.columns:
        raise KeyError(
            f"Origination PD column not found in staging input: {origination_pd_column}"
        )

    return pd.to_numeric(df[origination_pd_column], errors="coerce").clip(lower=0.0001)


def _combine_flag_columns(df: pd.DataFrame, columns: Sequence[str]) -> pd.Series:
    """Aggregates optional flag columns into a single boolean trigger."""

    existing_columns = [column for column in columns if column in df.columns]
    if not existing_columns:
        return pd.Series(False, index=df.index)

    flag_series = [_normalize_flag(df[column]) for column in existing_columns]
    flag_frame = pd.concat(flag_series, axis=1)
    return flag_frame.any(axis=1)


def _normalize_flag(series: pd.Series) -> pd.Series:
    """Normalizes a flag column to a boolean Series."""

    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)

    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce").fillna(0.0).gt(0.0)

    normalized = series.fillna("").astype(str).str.strip().str.lower()
    return normalized.isin({"1", "true", "t", "yes", "y", "sim"})
