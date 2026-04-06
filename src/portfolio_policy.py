from __future__ import annotations

import numpy as np
import pandas as pd


def build_sector_policy_flags(
    exposure_df: pd.DataFrame,
    upper_concentration_limit: float = 0.25,
    high_risk_cost_limit: float = 0.08,
) -> pd.DataFrame:
    out = exposure_df.copy()
    out["is_concentrated"] = out["ead_share"] >= upper_concentration_limit
    out["is_high_risk_cost"] = out["risk_cost"] >= high_risk_cost_limit

    def recommendation(row: pd.Series) -> str:
        if row["is_concentrated"] and row["is_high_risk_cost"]:
            return "tighten_credit"
        if row["is_concentrated"] and not row["is_high_risk_cost"]:
            return "hold_and_monitor"
        if (not row["is_concentrated"]) and (not row["is_high_risk_cost"]):
            return "prefer_growth"
        return "price_for_risk"

    out["recommendation"] = out.apply(recommendation, axis=1)
    return out


def indicative_sector_pricing(
    exposure_df: pd.DataFrame,
    base_spread: float = 0.05,
) -> pd.DataFrame:
    out = exposure_df.copy()
    out["indicative_spread"] = (
        base_spread
        + 0.40 * out["avg_pd"]
        + 0.20 * out["avg_lgd"]
        + 0.10 * out["ead_share"]
    )
    return out


def normalize_series(s: pd.Series) -> pd.Series:
    s = s.astype(float)
    min_v = s.min()
    max_v = s.max()
    if np.isclose(max_v - min_v, 0.0):
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - min_v) / (max_v - min_v)


def dominant_sectors(exposure_df: pd.DataFrame, top_n: int = 3) -> list[str]:
    return exposure_df.sort_values("total_ead", ascending=False)["sector"].head(top_n).tolist()


def marginal_correlation_to_dominant_book(
    corr_matrix: pd.DataFrame,
    dominant_book: list[str],
) -> pd.Series:
    values: dict[str, float] = {}
    for sector in corr_matrix.columns:
        refs = [s for s in dominant_book if s in corr_matrix.columns and s != sector]
        if not refs:
            values[sector] = 0.0
        else:
            values[sector] = float(corr_matrix.loc[sector, refs].mean())
    return pd.Series(values, name="marginal_corr_to_book")


def build_sector_attractiveness_index(
    exposure_df: pd.DataFrame,
    corr_matrix: pd.DataFrame,
    top_n_dominant: int = 3,
    w_spread: float = 0.30,
    w_pd: float = 0.25,
    w_lgd: float = 0.15,
    w_concentration: float = 0.15,
    w_corr: float = 0.15,
) -> pd.DataFrame:
    out = exposure_df.copy()

    dominant_book = dominant_sectors(out, top_n=top_n_dominant)
    marginal_corr = marginal_correlation_to_dominant_book(corr_matrix, dominant_book)

    out = out.merge(
        marginal_corr.rename_axis("sector").reset_index(),
        on="sector",
        how="left",
    )

    out["pd_penalty"] = normalize_series(out["avg_pd"])
    out["lgd_penalty"] = normalize_series(out["avg_lgd"])
    out["concentration_penalty"] = normalize_series(out["ead_share"])
    out["corr_penalty"] = normalize_series(out["marginal_corr_to_book"])
    out["spread_reward"] = normalize_series(out["indicative_spread"])

    out["sector_attractiveness_index"] = (
        w_spread * out["spread_reward"]
        - w_pd * out["pd_penalty"]
        - w_lgd * out["lgd_penalty"]
        - w_concentration * out["concentration_penalty"]
        - w_corr * out["corr_penalty"]
    )

    out["sector_attractiveness_rank"] = (
        out["sector_attractiveness_index"]
        .rank(ascending=False, method="dense")
        .astype(int)
    )

    q75 = out["sector_attractiveness_index"].quantile(0.75)
    q25 = out["sector_attractiveness_index"].quantile(0.25)

    def strategic_bucket(row: pd.Series) -> str:
        if row["sector_attractiveness_index"] >= q75:
            return "expand_selectively"
        if row["sector_attractiveness_index"] <= q25:
            return "restrict_or_reprice"
        return "neutral_monitoring"

    out["strategic_bucket"] = out.apply(strategic_bucket, axis=1)

    score_raw = out["sector_attractiveness_index"]

    out["sector_attractiveness_score_0_100"] = 100 * (
        (score_raw - score_raw.min()) / (score_raw.max() - score_raw.min())
    )

    out["ecl_share"] = out["total_ecl"] / out["total_ecl"].sum()

    out = out.sort_values(
        ["sector_attractiveness_rank", "sector_attractiveness_index"],
        ascending=[True, False],
    ).reset_index(drop=True)

    return out