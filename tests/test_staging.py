from __future__ import annotations

import unittest

import pandas as pd

from src.staging import assign_stage


class AssignStageTests(unittest.TestCase):
    def _base_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "dpd": [0],
                "true_pd_12m": [0.03],
                "default_12m": [0],
            }
        )

    def test_healthy_client_remains_stage_one(self) -> None:
        df = self._base_frame()

        stage = assign_stage(df, pd.Series([0.04]))

        self.assertEqual(stage.iloc[0], 1)

    def test_future_default_label_does_not_force_stage_three(self) -> None:
        df = self._base_frame()
        df.loc[0, "default_12m"] = 1

        stage = assign_stage(df, pd.Series([0.04]))

        self.assertEqual(stage.iloc[0], 1)

    def test_dpd_over_thirty_days_moves_to_stage_two(self) -> None:
        df = self._base_frame()
        df.loc[0, "dpd"] = 30

        stage = assign_stage(df, pd.Series([0.04]))

        self.assertEqual(stage.iloc[0], 2)

    def test_material_pd_increase_without_delinquency_moves_to_stage_two(self) -> None:
        df = self._base_frame()
        df.loc[0, "true_pd_12m"] = 0.02

        stage = assign_stage(df, pd.Series([0.10]))

        self.assertEqual(stage.iloc[0], 2)

    def test_dpd_over_ninety_days_moves_to_stage_three(self) -> None:
        df = self._base_frame()
        df.loc[0, "dpd"] = 90

        stage = assign_stage(df, pd.Series([0.04]))

        self.assertEqual(stage.iloc[0], 3)

    def test_most_severe_trigger_prevails(self) -> None:
        df = self._base_frame()
        df.loc[0, "dpd"] = 35
        df.loc[0, "watchlist_flag"] = 1
        df.loc[0, "restructured_flag"] = 1

        stage = assign_stage(df, pd.Series([0.12]))

        self.assertEqual(stage.iloc[0], 3)


if __name__ == "__main__":
    unittest.main()
