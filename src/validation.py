from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score


def population_stability_index(expected: pd.Series, actual: pd.Series, buckets: int = 10) -> float:
    quantiles = np.unique(np.quantile(expected, np.linspace(0, 1, buckets + 1)))
    if len(quantiles) < 3:
        return 0.0

    exp_bins = pd.cut(expected, bins=quantiles, include_lowest=True)
    act_bins = pd.cut(actual, bins=quantiles, include_lowest=True)

    exp_dist = exp_bins.value_counts(normalize=True, sort=False) + 1e-6
    act_dist = act_bins.value_counts(normalize=True, sort=False) + 1e-6

    psi = ((act_dist - exp_dist) * np.log(act_dist / exp_dist)).sum()
    return float(psi)


def calibration_table(y_true: pd.Series, y_prob: pd.Series, buckets: int = 10) -> pd.DataFrame:
    df = pd.DataFrame({"y_true": y_true, "y_prob": y_prob})
    df["bucket"] = pd.qcut(df["y_prob"], q=buckets, duplicates="drop")
    out = df.groupby("bucket", observed=False).agg(
        avg_pd=("y_prob", "mean"),
        obs_rate=("y_true", "mean"),
        n=("y_true", "size"),
    ).reset_index()
    return out


def score_pd_model(y_true: pd.Series, y_prob: pd.Series) -> dict[str, float]:
    return {
        "auc": float(roc_auc_score(y_true, y_prob)),
        "brier": float(brier_score_loss(y_true, y_prob)),
    }