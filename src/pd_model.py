from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.feature_engineering import CATEGORICAL_FEATURES, NUMERIC_FEATURES, build_model_matrix


@dataclass
class PDModelResult:
    model: Pipeline
    features: list[str]
    auc: float
    brier: float


class PDModel:
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.features: list[str] = []

        self.preprocessor = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), NUMERIC_FEATURES),
            ],
            remainder="passthrough",
        )

        self.model = Pipeline(
            steps=[
                ("preprocessor", self.preprocessor),
                (
                    "classifier",
                    LogisticRegression(
                        max_iter=5000,
                        random_state=random_state,
                        solver="lbfgs",
                    ),
                ),
            ]
        )

    def fit(self, df: pd.DataFrame) -> PDModelResult:
        x = build_model_matrix(df)
        y = df["default_12m"]
        self.features = x.columns.tolist()

        x_train, x_test, y_train, y_test = train_test_split(
            x,
            y,
            test_size=0.25,
            random_state=self.random_state,
            stratify=y,
        )

        numeric_cols_present = [c for c in NUMERIC_FEATURES if c in x.columns]
        passthrough_cols = [c for c in x.columns if c not in numeric_cols_present]

        self.preprocessor = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), numeric_cols_present),
            ],
            remainder="passthrough",
        )

        self.model = Pipeline(
            steps=[
                ("preprocessor", self.preprocessor),
                (
                    "classifier",
                    LogisticRegression(
                        max_iter=5000,
                        random_state=self.random_state,
                        solver="lbfgs",
                    ),
                ),
            ]
        )

        self.model.fit(x_train, y_train)
        p = self.model.predict_proba(x_test)[:, 1]

        auc = roc_auc_score(y_test, p)
        brier = brier_score_loss(y_test, p)
        return PDModelResult(self.model, self.features, auc, brier)

    def predict_pd_12m(self, df: pd.DataFrame) -> np.ndarray:
        x = build_model_matrix(df)
        x = x.reindex(columns=self.features, fill_value=0)
        return self.model.predict_proba(x)[:, 1]