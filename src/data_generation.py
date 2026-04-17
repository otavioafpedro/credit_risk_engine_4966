from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd


class SyntheticCreditDataGenerator:
    def __init__(
        self,
        n_clients: int = 8000,
        random_state: int = 42,
        macro_factors: Mapping[str, float] | None = None,
    ):
        self.n_clients = n_clients
        self.random_state = random_state
        self.rng = np.random.default_rng(random_state)
        self.macro_factors = dict(macro_factors) if macro_factors is not None else None

    def generate(self) -> pd.DataFrame:
        ids = np.arange(1, self.n_clients + 1)

        age = self.rng.integers(21, 75, self.n_clients)
        income = self.rng.lognormal(mean=8.5, sigma=0.55, size=self.n_clients)
        ltv = np.clip(self.rng.normal(0.58, 0.18, self.n_clients), 0.05, 1.40)
        dti = np.clip(self.rng.normal(0.32, 0.15, self.n_clients), 0.01, 1.20)
        bureau_score = np.clip(self.rng.normal(680, 85, self.n_clients), 300, 900)
        utilization = np.clip(self.rng.beta(2.4, 3.2, self.n_clients), 0.0, 1.0)
        months_on_book = self.rng.integers(1, 121, self.n_clients)
        dpd = self.rng.choice(
            [0, 5, 15, 30, 60, 90, 120],
            size=self.n_clients,
            p=[0.62, 0.10, 0.09, 0.08, 0.06, 0.03, 0.02],
        )
        has_collateral = self.rng.choice([0, 1], size=self.n_clients, p=[0.35, 0.65])
        segment = self.rng.choice(["retail", "sme"], size=self.n_clients, p=[0.82, 0.18])
        product = self.rng.choice(
            ["personal_loan", "credit_card", "auto_loan", "working_capital"],
            size=self.n_clients,
            p=[0.35, 0.30, 0.20, 0.15],
        )
        sector = self.rng.choice(
            ["agribusiness", "retail", "industry", "technology", "healthcare", "utilities", "transport"],
            size=self.n_clients,
            p=[0.14, 0.24, 0.16, 0.10, 0.12, 0.12, 0.12],
        )

        balance = np.exp(self.rng.normal(9.1, 0.9, self.n_clients))
        undrawn = np.exp(self.rng.normal(7.0, 1.0, self.n_clients)) * (product == "credit_card")

        unemployment, selic_proxy, gdp_growth = self._build_macro_columns()
        watchlist_flag, restructured_flag, financial_distress_flag, problem_asset_flag = (
            self._build_observed_distress_flags(
                income=income,
                bureau_score=bureau_score,
                utilization=utilization,
                months_on_book=months_on_book,
                dpd=dpd,
                dti=dti,
                segment=segment,
            )
        )

        sector_risk_map = {
            "agribusiness": -0.10,
            "retail": 0.18,
            "industry": 0.08,
            "technology": 0.02,
            "healthcare": -0.05,
            "utilities": -0.12,
            "transport": 0.10,
        }
        sector_risk = pd.Series(sector).map(sector_risk_map).values

        linear_score = (
            -4.9
            + 1.6 * dti
            + 1.8 * utilization
            + 1.2 * ltv
            - 0.0045 * bureau_score
            + 0.012 * np.maximum(dpd, 0)
            + 2.5 * unemployment
            + 1.2 * selic_proxy
            - 3.0 * gdp_growth
            - 0.45 * has_collateral
            + 0.35 * (segment == "sme").astype(int)
            + 0.25 * (product == "credit_card").astype(int)
            + sector_risk
        )

        true_pd_12m = 1 / (1 + np.exp(-linear_score))
        default_12m = self.rng.binomial(1, np.clip(true_pd_12m, 0.001, 0.95))

        lgd_base = (
            0.72
            + 0.22 * ltv
            + 0.14 * (1 - has_collateral)
            + 0.10 * (product == "credit_card").astype(int)
            - 0.00035 * bureau_score
        )
        true_lgd = np.clip(lgd_base + self.rng.normal(0, 0.08, self.n_clients), 0.05, 0.98)

        ccf = np.clip(
            0.55
            + 0.25 * utilization
            + 0.10 * (product == "credit_card").astype(int)
            + self.rng.normal(0, 0.06, self.n_clients),
            0.0,
            1.0,
        )
        true_ead = balance + undrawn * ccf

        df = pd.DataFrame(
            {
                "client_id": ids,
                "age": age,
                "income": income,
                "ltv": ltv,
                "dti": dti,
                "bureau_score": bureau_score,
                "utilization": utilization,
                "months_on_book": months_on_book,
                "dpd": dpd,
                "has_collateral": has_collateral,
                "segment": segment,
                "product": product,
                "sector": sector,
                "balance": balance,
                "undrawn": undrawn,
                "unemployment": unemployment,
                "selic_proxy": selic_proxy,
                "gdp_growth": gdp_growth,
                "watchlist_flag": watchlist_flag,
                "restructured_flag": restructured_flag,
                "financial_distress_flag": financial_distress_flag,
                "problem_asset_flag": problem_asset_flag,
                "true_pd_12m": np.clip(true_pd_12m, 0.0001, 0.9999),
                "default_12m": default_12m,
                "true_lgd": true_lgd,
                "ccf": ccf,
                "true_ead": true_ead,
            }
        )

        return df

    def _build_macro_columns(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if self.macro_factors is None:
            unemployment = self.rng.normal(0.085, 0.012, self.n_clients)
            selic_proxy = self.rng.normal(0.115, 0.015, self.n_clients)
            gdp_growth = self.rng.normal(0.020, 0.015, self.n_clients)
            return unemployment, selic_proxy, gdp_growth

        required_factors = ("unemployment", "selic_proxy", "gdp_growth")
        missing_factors = [factor for factor in required_factors if factor not in self.macro_factors]
        if missing_factors:
            raise ValueError(
                "Fatores macro reais incompletos para a geracao da carteira. "
                f"Campos ausentes: {', '.join(missing_factors)}"
            )

        return (
            np.full(self.n_clients, float(self.macro_factors["unemployment"])),
            np.full(self.n_clients, float(self.macro_factors["selic_proxy"])),
            np.full(self.n_clients, float(self.macro_factors["gdp_growth"])),
        )

    def _build_observed_distress_flags(
        self,
        income: np.ndarray,
        bureau_score: np.ndarray,
        utilization: np.ndarray,
        months_on_book: np.ndarray,
        dpd: np.ndarray,
        dti: np.ndarray,
        segment: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Builds observable distress flags without relying on future default outcomes."""

        watchlist_flag = (
            (
                (dpd >= 15)
                & (
                    (bureau_score < 620)
                    | (utilization > 0.75)
                    | (dti > 0.45)
                )
            )
            | ((bureau_score < 540) & (segment == "sme"))
        ).astype(int)

        income_p10 = np.quantile(income, 0.10)
        restructured_flag = (
            ((dpd >= 60) & (months_on_book >= 12) & (dti > 0.60))
            | ((dti > 0.85) & (bureau_score < 500) & (months_on_book >= 12))
        ).astype(int)

        financial_distress_flag = (
            ((dpd >= 60) & (utilization > 0.90) & (dti > 0.55))
            | (
                (income <= income_p10)
                & (dti > 0.85)
                & (bureau_score < 500)
                & (utilization > 0.80)
            )
        ).astype(int)

        problem_asset_flag = (
            (dpd >= 90)
            | ((restructured_flag == 1) & (financial_distress_flag == 1))
        ).astype(int)

        return (
            watchlist_flag,
            restructured_flag,
            financial_distress_flag,
            problem_asset_flag,
        )
