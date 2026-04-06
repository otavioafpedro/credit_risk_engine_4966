from __future__ import annotations

import numpy as np
import pandas as pd


def build_lifetime_pd(pd_12m: np.ndarray, months_forward: int = 24) -> np.ndarray:
    pd_12m = np.clip(pd_12m, 1e-6, 0.999)
    monthly_hazard = 1 - np.power(1 - pd_12m, 1 / 12)

    curves = []
    survival = np.ones_like(pd_12m)
    cumulative_default = np.zeros_like(pd_12m)

    for _ in range(months_forward):
        marginal_default = survival * monthly_hazard
        cumulative_default = cumulative_default + marginal_default
        survival = survival * (1 - monthly_hazard)
        curves.append(cumulative_default.copy())

    return np.column_stack(curves)


def discount_factor(month: int, annual_rate: float = 0.12) -> float:
    monthly = (1 + annual_rate) ** (1 / 12) - 1
    return 1 / ((1 + monthly) ** month)


def calculate_ecl(
    pd_12m: np.ndarray,
    lgd: np.ndarray,
    ead: np.ndarray,
    stage: pd.Series,
    months_forward: int = 24,
    annual_rate: float = 0.12,
) -> pd.DataFrame:
    lifetime_curve = build_lifetime_pd(pd_12m, months_forward=months_forward)

    out = pd.DataFrame(
        {
            "pd_12m_model": pd_12m,
            "lgd_model": lgd,
            "ead_model": ead,
            "stage": stage.values,
        }
    )

    stage1_ecl = pd_12m * lgd * ead * discount_factor(12, annual_rate)

    lifetime_ecl = np.zeros_like(pd_12m)
    prev = np.zeros_like(pd_12m)

    for m in range(months_forward):
        cumulative = lifetime_curve[:, m]
        marginal = np.clip(cumulative - prev, 0.0, 1.0)
        lifetime_ecl += marginal * lgd * ead * discount_factor(m + 1, annual_rate)
        prev = cumulative

    out["ecl_12m"] = stage1_ecl
    out["ecl_lifetime"] = lifetime_ecl
    out["final_ecl"] = np.where(out["stage"] == 1, out["ecl_12m"], out["ecl_lifetime"])

    return out