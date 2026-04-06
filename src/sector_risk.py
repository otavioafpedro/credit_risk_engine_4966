from __future__ import annotations

import numpy as np
import pandas as pd


def sector_exposure_summary(df: pd.DataFrame) -> pd.DataFrame:
    out = df.groupby("sector", observed=False).agg(
        n_clients=("client_id", "count"),
        total_ead=("ead_model", "sum"),
        total_ecl=("final_ecl", "sum"),
        avg_pd=("pd_12m_model", "mean"),
        avg_lgd=("lgd_model", "mean"),
        avg_stage=("stage", "mean"),
    ).reset_index()

    total_portfolio_ead = out["total_ead"].sum()
    out["ead_share"] = out["total_ead"] / total_portfolio_ead
    out["risk_cost"] = out["total_ecl"] / out["total_ead"].clip(lower=1e-9)
    out = out.sort_values("total_ead", ascending=False).reset_index(drop=True)
    return out


def sector_hhi(exposure_df: pd.DataFrame) -> float:
    shares = exposure_df["ead_share"].values
    return float(np.sum(np.square(shares)))


def build_sector_time_series(n_months: int = 36, random_state: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(random_state)
    dates = pd.date_range("2023-01-01", periods=n_months, freq="MS")

    macro_1 = rng.normal(0, 1, n_months)
    macro_2 = rng.normal(0, 1, n_months)
    macro_3 = rng.normal(0, 1, n_months)

    sector_beta = {
        "agribusiness": (0.4, -0.1, 0.2),
        "retail": (0.8, 0.5, -0.1),
        "industry": (0.7, 0.2, 0.3),
        "technology": (0.3, 0.8, -0.2),
        "healthcare": (0.1, -0.2, 0.1),
        "utilities": (-0.1, -0.3, 0.5),
        "transport": (0.6, 0.3, 0.4),
    }

    base_pd_map = {
        "agribusiness": 0.030,
        "retail": 0.065,
        "industry": 0.050,
        "technology": 0.045,
        "healthcare": 0.028,
        "utilities": 0.022,
        "transport": 0.055,
    }

    rows: list[dict] = []
    for sector, (b1, b2, b3) in sector_beta.items():
        noise = rng.normal(0, 0.35, n_months)
        stress_index = b1 * macro_1 + b2 * macro_2 + b3 * macro_3 + noise
        pd_series = np.clip(base_pd_map[sector] + 0.015 * stress_index, 0.005, 0.35)

        for d, pd_value in zip(dates, pd_series):
            rows.append(
                {
                    "date": d,
                    "sector": sector,
                    "sector_pd": pd_value,
                }
            )

    return pd.DataFrame(rows)


def sector_correlation_matrix(sector_ts: pd.DataFrame) -> pd.DataFrame:
    pivot = sector_ts.pivot(index="date", columns="sector", values="sector_pd")
    return pivot.corr()


def find_natural_hedges(corr_matrix: pd.DataFrame, threshold: float = 0.0) -> pd.DataFrame:
    rows: list[dict] = []
    sectors = corr_matrix.columns.tolist()

    for i in range(len(sectors)):
        for j in range(i + 1, len(sectors)):
            corr = float(corr_matrix.iloc[i, j])
            if corr <= threshold:
                rows.append(
                    {
                        "sector_a": sectors[i],
                        "sector_b": sectors[j],
                        "correlation": corr,
                    }
                )

    if not rows:
        return pd.DataFrame(columns=["sector_a", "sector_b", "correlation"])

    return pd.DataFrame(rows).sort_values("correlation", ascending=True).reset_index(drop=True)