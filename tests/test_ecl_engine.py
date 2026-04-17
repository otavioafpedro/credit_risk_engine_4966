from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.ecl_engine import calculate_probability_weighted_ecl, discount_factor


class ProbabilityWeightedECLTests(unittest.TestCase):
    def _scenario_config(self) -> dict[str, dict[str, float]]:
        return {
            "base": {"weight": 0.60, "pd_multiplier": 1.00, "lgd_multiplier": 1.00},
            "adverse": {"weight": 0.30, "pd_multiplier": 1.20, "lgd_multiplier": 1.05},
            "severe": {"weight": 0.10, "pd_multiplier": 1.50, "lgd_multiplier": 1.10},
        }

    def test_probability_weighted_sum_matches_scenario_decomposition(self) -> None:
        result = calculate_probability_weighted_ecl(
            pd_12m=np.array([0.10]),
            lgd=np.array([0.50]),
            ead=np.array([100.0]),
            stage=pd.Series([1]),
            scenario_config=self._scenario_config(),
        )

        detail = result.ecl_frame.iloc[0]
        expected_weighted = (
            detail["ecl_base"] * 0.60
            + detail["ecl_adverse"] * 0.30
            + detail["ecl_severe"] * 0.10
        )

        self.assertAlmostEqual(detail["final_ecl_weighted"], expected_weighted, places=10)

    def test_weights_are_normalized_when_input_sum_differs_from_one(self) -> None:
        scenario_config = {
            "base": {"weight": 6.0, "pd_multiplier": 1.00, "lgd_multiplier": 1.00},
            "adverse": {"weight": 3.0, "pd_multiplier": 1.20, "lgd_multiplier": 1.05},
            "severe": {"weight": 1.0, "pd_multiplier": 1.50, "lgd_multiplier": 1.10},
        }

        result = calculate_probability_weighted_ecl(
            pd_12m=np.array([0.10]),
            lgd=np.array([0.50]),
            ead=np.array([100.0]),
            stage=pd.Series([1]),
            scenario_config=scenario_config,
        )

        summary = result.scenario_summary.set_index("scenario")

        self.assertTrue(bool(summary.loc["base", "weights_normalized"]))
        self.assertAlmostEqual(summary["normalized_weight"].sum(), 1.0, places=12)
        self.assertAlmostEqual(summary.loc["base", "normalized_weight"], 0.60, places=12)
        self.assertAlmostEqual(summary.loc["adverse", "normalized_weight"], 0.30, places=12)
        self.assertAlmostEqual(summary.loc["severe", "normalized_weight"], 0.10, places=12)

    def test_pd_and_lgd_are_clipped_before_scenario_ecl(self) -> None:
        result = calculate_probability_weighted_ecl(
            pd_12m=np.array([1.40]),
            lgd=np.array([1.30]),
            ead=np.array([100.0]),
            stage=pd.Series([1]),
            scenario_config={
                "base": {"weight": 1.0, "pd_multiplier": 1.00, "lgd_multiplier": 1.00}
            },
        )

        detail = result.ecl_frame.iloc[0]
        expected_ecl = 0.999 * 1.0 * 100.0 * discount_factor(12, annual_rate=0.12)

        self.assertAlmostEqual(detail["ecl_base"], expected_ecl, places=8)

    def test_stage_one_and_stage_two_use_expected_horizon_in_each_scenario(self) -> None:
        result = calculate_probability_weighted_ecl(
            pd_12m=np.array([0.08, 0.08]),
            lgd=np.array([0.50, 0.50]),
            ead=np.array([100.0, 100.0]),
            stage=pd.Series([1, 2]),
            scenario_config=self._scenario_config(),
        )

        detail = result.ecl_frame

        self.assertAlmostEqual(detail.loc[0, "ecl_base"], detail.loc[0, "ecl_12m_base"], places=10)
        self.assertAlmostEqual(detail.loc[1, "ecl_base"], detail.loc[1, "ecl_lifetime_base"], places=10)
        self.assertAlmostEqual(detail.loc[0, "ecl_severe"], detail.loc[0, "ecl_12m_severe"], places=10)
        self.assertAlmostEqual(detail.loc[1, "ecl_severe"], detail.loc[1, "ecl_lifetime_severe"], places=10)

    def test_reference_date_is_available_in_scenario_audit(self) -> None:
        result = calculate_probability_weighted_ecl(
            pd_12m=np.array([0.10]),
            lgd=np.array([0.50]),
            ead=np.array([100.0]),
            stage=pd.Series([1]),
            scenario_config=self._scenario_config(),
            reference_date="2026-04-30",
        )

        summary = result.scenario_summary
        self.assertTrue((summary["macro_reference_date"] == "2026-04-30").all())


if __name__ == "__main__":
    unittest.main()
