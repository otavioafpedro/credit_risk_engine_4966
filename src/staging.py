from __future__ import annotations

import numpy as np
import pandas as pd


def assign_stage(
    df: pd.DataFrame,
    pd_12m: np.ndarray,
    stage2_pd_multiplier: float = 2.0,
    stage2_dpd_threshold: int = 30,
    stage3_dpd_threshold: int = 90,
) -> pd.Series:
    origination_pd = df["true_pd_12m"].clip(lower=0.0001)
    ratio = pd.Series(pd_12m, index=df.index) / origination_pd

    stage = pd.Series(1, index=df.index, dtype=int)
    stage[(df["dpd"] >= stage2_dpd_threshold) | (ratio >= stage2_pd_multiplier)] = 2
    stage[df["dpd"] >= stage3_dpd_threshold] = 3
    stage[df["default_12m"] == 1] = 3

    return stage