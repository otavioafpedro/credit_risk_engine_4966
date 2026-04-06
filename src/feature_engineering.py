from __future__ import annotations

import pandas as pd


NUMERIC_FEATURES = [
    "age",
    "income",
    "ltv",
    "dti",
    "bureau_score",
    "utilization",
    "months_on_book",
    "dpd",
    "has_collateral",
    "balance",
    "undrawn",
    "unemployment",
    "selic_proxy",
    "gdp_growth",
]

CATEGORICAL_FEATURES = ["segment", "product", "sector"]


def build_model_matrix(df: pd.DataFrame) -> pd.DataFrame:
    base = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES].copy()
    base = pd.get_dummies(base, columns=CATEGORICAL_FEATURES, drop_first=True)
    return base