from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
import pandas as pd


ScenarioOverride = Mapping[str, Any]


@dataclass
class ProbabilityWeightedECLResult:
    """Packages the detailed weighted ECL output and scenario audit summary."""

    ecl_frame: pd.DataFrame
    scenario_summary: pd.DataFrame


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
    clipped_pd, clipped_lgd, clipped_ead, stage_series = _prepare_ecl_inputs(
        pd_12m=pd_12m,
        lgd=lgd,
        ead=ead,
        stage=stage,
    )
    lifetime_curve = build_lifetime_pd(clipped_pd, months_forward=months_forward)

    out = pd.DataFrame(
        {
            "pd_12m_model": clipped_pd,
            "lgd_model": clipped_lgd,
            "ead_model": clipped_ead,
            "stage": stage_series.values,
        }
    )

    stage1_ecl = clipped_pd * clipped_lgd * clipped_ead * discount_factor(12, annual_rate)

    lifetime_ecl = np.zeros_like(clipped_pd)
    prev = np.zeros_like(clipped_pd)

    for m in range(months_forward):
        cumulative = lifetime_curve[:, m]
        marginal = np.clip(cumulative - prev, 0.0, 1.0)
        lifetime_ecl += marginal * clipped_lgd * clipped_ead * discount_factor(m + 1, annual_rate)
        prev = cumulative

    out["ecl_12m"] = stage1_ecl
    out["ecl_lifetime"] = lifetime_ecl
    out["final_ecl"] = np.where(out["stage"] == 1, out["ecl_12m"], out["ecl_lifetime"])

    return out


def calculate_probability_weighted_ecl(
    pd_12m: np.ndarray,
    lgd: np.ndarray,
    ead: np.ndarray,
    stage: pd.Series,
    scenario_config: Mapping[str, Mapping[str, float]],
    months_forward: int = 24,
    annual_rate: float = 0.12,
    reference_date: str | pd.Timestamp | None = None,
    scenario_overrides: Mapping[str, ScenarioOverride] | None = None,
) -> ProbabilityWeightedECLResult:
    """Calculates scenario ECLs and the final probability-weighted impairment.

    By default, the function applies each scenario's PD and LGD multipliers to the
    base arrays. When a scenario override is provided, the override takes precedence.
    This allows the main pipeline to pass scenario-specific stressed PD, LGD, EAD
    and stage values while keeping one reusable weighted-ECL engine.
    """

    base_pd, base_lgd, base_ead, base_stage = _prepare_ecl_inputs(
        pd_12m=pd_12m,
        lgd=lgd,
        ead=ead,
        stage=stage,
    )
    normalized_summary = _normalize_scenario_summary(scenario_config, reference_date)
    overrides = scenario_overrides or {}

    detail = pd.DataFrame(
        {
            "pd_12m_model": base_pd,
            "lgd_model": base_lgd,
            "ead_model": base_ead,
            "stage": base_stage.values,
        }
    )

    weighted_total = np.zeros_like(base_pd, dtype=float)
    summary_rows: list[dict[str, object]] = []

    for scenario_row in normalized_summary.to_dict(orient="records"):
        scenario_name = str(scenario_row["scenario"])
        scenario_override = overrides.get(scenario_name, {})

        scenario_pd = scenario_override.get(
            "pd_12m",
            np.asarray(base_pd, dtype=float) * float(scenario_row["pd_multiplier"]),
        )
        scenario_lgd = scenario_override.get(
            "lgd",
            np.asarray(base_lgd, dtype=float) * float(scenario_row["lgd_multiplier"]),
        )
        scenario_ead = scenario_override.get("ead", base_ead)
        scenario_stage = scenario_override.get("stage", base_stage)

        scenario_ecl = calculate_ecl(
            pd_12m=np.asarray(scenario_pd, dtype=float),
            lgd=np.asarray(scenario_lgd, dtype=float),
            ead=np.asarray(scenario_ead, dtype=float),
            stage=_coerce_stage_series(scenario_stage, index=base_stage.index),
            months_forward=months_forward,
            annual_rate=annual_rate,
        )

        detail[f"ecl_12m_{scenario_name}"] = scenario_ecl["ecl_12m"].values
        detail[f"ecl_lifetime_{scenario_name}"] = scenario_ecl["ecl_lifetime"].values
        detail[f"ecl_{scenario_name}"] = scenario_ecl["final_ecl"].values

        if scenario_name == "base":
            detail["ecl_12m"] = scenario_ecl["ecl_12m"].values
            detail["ecl_lifetime"] = scenario_ecl["ecl_lifetime"].values

        weighted_total += scenario_ecl["final_ecl"].values * float(scenario_row["normalized_weight"])

        summary_rows.append(
            {
                **scenario_row,
                "total_ecl": float(scenario_ecl["final_ecl"].sum()),
                "avg_pd": float(scenario_ecl["pd_12m_model"].mean()),
                "avg_lgd": float(scenario_ecl["lgd_model"].mean()),
                "avg_ead": float(scenario_ecl["ead_model"].mean()),
                "stage1_share": float((scenario_ecl["stage"] == 1).mean()),
                "stage2_share": float((scenario_ecl["stage"] == 2).mean()),
                "stage3_share": float((scenario_ecl["stage"] == 3).mean()),
                "stage2_plus_share": float((scenario_ecl["stage"] >= 2).mean()),
            }
        )

    detail["final_ecl_weighted"] = weighted_total
    detail["final_ecl"] = detail["final_ecl_weighted"]

    scenario_summary = pd.DataFrame(summary_rows)
    return ProbabilityWeightedECLResult(ecl_frame=detail, scenario_summary=scenario_summary)


def _prepare_ecl_inputs(
    pd_12m: np.ndarray,
    lgd: np.ndarray,
    ead: np.ndarray,
    stage: pd.Series,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, pd.Series]:
    """Normalizes ECL inputs before scenario calculations."""

    clipped_pd = np.clip(np.asarray(pd_12m, dtype=float), 1e-6, 0.999)
    clipped_lgd = np.clip(np.asarray(lgd, dtype=float), 0.0, 1.0)
    clipped_ead = np.clip(np.asarray(ead, dtype=float), 0.0, None)
    stage_series = _coerce_stage_series(stage)
    return clipped_pd, clipped_lgd, clipped_ead, stage_series


def _coerce_stage_series(stage: pd.Series | np.ndarray | list[int], index: pd.Index | None = None) -> pd.Series:
    """Builds an integer stage series aligned with the provided index."""

    if isinstance(stage, pd.Series):
        stage_series = stage.astype(int)
        if index is not None:
            stage_series = stage_series.reindex(index)
        return stage_series

    if index is None:
        stage_array = np.asarray(stage, dtype=int)
        index = pd.RangeIndex(len(stage_array))
    return pd.Series(np.asarray(stage, dtype=int), index=index, dtype=int)


def _normalize_scenario_summary(
    scenario_config: Mapping[str, Mapping[str, float]],
    reference_date: str | pd.Timestamp | None,
) -> pd.DataFrame:
    """Returns a normalized audit table for scenario weights and overlays."""

    if not scenario_config:
        raise ValueError("At least one scenario is required for probability-weighted ECL.")

    rows: list[dict[str, object]] = []
    input_weight_sum = 0.0
    for scenario_name, config in scenario_config.items():
        input_weight = float(config.get("weight", 0.0))
        if input_weight < 0.0:
            raise ValueError(f"Scenario weight cannot be negative: {scenario_name}")
        input_weight_sum += input_weight

        rows.append(
            {
                "scenario": scenario_name,
                "input_weight": input_weight,
                "pd_multiplier": float(config.get("pd_multiplier", 1.0)),
                "lgd_multiplier": float(config.get("lgd_multiplier", 1.0)),
                "unemployment_shift": float(config.get("unemployment_shift", 0.0)),
                "selic_shift": float(config.get("selic_shift", 0.0)),
                "gdp_shift": float(config.get("gdp_shift", 0.0)),
            }
        )

    if input_weight_sum <= 0.0:
        raise ValueError("Scenario weights must sum to a positive number.")

    weights_normalized = not np.isclose(input_weight_sum, 1.0)
    reference_date_str = _format_reference_date(reference_date)

    for row in rows:
        row["input_weight_sum"] = input_weight_sum
        row["normalized_weight"] = float(row["input_weight"]) / input_weight_sum
        row["weights_normalized"] = weights_normalized
        row["macro_reference_date"] = reference_date_str

    return pd.DataFrame(rows)


def _format_reference_date(reference_date: str | pd.Timestamp | None) -> str | None:
    """Formats the optional macro snapshot date for audit outputs."""

    if reference_date is None:
        return None

    return pd.Timestamp(reference_date).strftime("%Y-%m-%d")
