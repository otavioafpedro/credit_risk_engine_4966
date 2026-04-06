from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

from src.feature_engineering import build_model_matrix


class LGDModel:
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.model = RandomForestRegressor(
            n_estimators=250,
            max_depth=8,
            min_samples_leaf=20,
            random_state=random_state,
            n_jobs=-1,
        )
        self.features: list[str] = []
        self.mae_: float | None = None

    def fit(self, df: pd.DataFrame) -> float:
        x = build_model_matrix(df)
        y = df["true_lgd"]
        self.features = x.columns.tolist()

        x_train, x_test, y_train, y_test = train_test_split(
            x,
            y,
            test_size=0.25,
            random_state=self.random_state,
        )

        self.model.fit(x_train, y_train)
        preds = np.clip(self.model.predict(x_test), 0.0, 1.0)
        self.mae_ = mean_absolute_error(y_test, preds)
        return self.mae_

    def predict_lgd(self, df: pd.DataFrame) -> np.ndarray:
        x = build_model_matrix(df)
        x = x.reindex(columns=self.features, fill_value=0)
        return np.clip(self.model.predict(x), 0.0, 1.0)