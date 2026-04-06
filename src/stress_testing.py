from __future__ import annotations

import numpy as np
import pandas as pd


SCENARIOS = {
    "base": {
        "unemployment_shift": 0.00,
        "selic_shift": 0.00,
        "gdp_shift": 0.00,
        "pd_multiplier": 1.00,
        "lgd_multiplier": 1.00,
    },
    "adverse": {
        "unemployment_shift": 0.02,
        "selic_shift": 0.02,
        "gdp_shift": -0.02,
        "pd_multiplier": 1.20,
        "lgd_multiplier": 1.05,
    },
    "severe": {
        "unemployment_shift": 0.04,
        "selic_shift": 0.04,
        "gdp_shift": -0.04,
        "pd_multiplier": 1.45,
        "lgd_multiplier": 1.10,
    },
}


def apply_scenario(df: pd.DataFrame, scenario_name: str) -> pd.DataFrame:
    scenario = SCENARIOS[scenario_name]
    stressed = df.copy()
    stressed["unemployment"] = stressed["unemployment"] + scenario["unemployment_shift"]
    stressed["selic_proxy"] = stressed["selic_proxy"] + scenario["selic_shift"]
    stressed["gdp_growth"] = stressed["gdp_growth"] + scenario["gdp_shift"]
    return stressed


def apply_macro_overlay(
    pd_values: np.ndarray,
    lgd_values: np.ndarray,
    scenario_name: str,
) -> tuple[np.ndarray, np.ndarray]:
    scenario = SCENARIOS[scenario_name]

    stressed_pd = np.clip(pd_values * scenario["pd_multiplier"], 1e-6, 0.999)
    stressed_lgd = np.clip(lgd_values * scenario["lgd_multiplier"], 0.0, 1.0)

    return stressed_pd, stressed_lgd