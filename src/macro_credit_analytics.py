from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from src.macro_feature_store import MacroFeatureStore
from src.stress_testing import SCENARIOS


@dataclass(frozen=True)
class AnalyticsSeriesDefinition:
    """Define como uma serie sera usada na camada analitica agregada."""

    output_name: str
    series_candidates: tuple[str, ...]
    transform: str
    description: str
    unit: str


@dataclass(frozen=True)
class RelationshipDefinition:
    """Define um relacionamento descritivo entre duas series agregadas."""

    relationship_name: str
    driver: str
    response: str
    description: str


@dataclass(frozen=True)
class MacroCreditAnalyticsResult:
    """Agrupa os artefatos principais da camada de analytics macro de credito."""

    reference_frame: pd.DataFrame
    selected_series: dict[str, str]
    reference_summary: pd.DataFrame
    relationship_summary: pd.DataFrame
    correlation_matrix: pd.DataFrame
    scenario_calibration: pd.DataFrame
    observed_scenario_overlays: pd.DataFrame
    validation_tables: dict[str, pd.DataFrame] = field(default_factory=dict)


ANALYTICS_SERIES_DEFINITIONS: tuple[AnalyticsSeriesDefinition, ...] = (
    AnalyticsSeriesDefinition(
        output_name="unemployment_rate",
        series_candidates=("br_unemployment_sidra_rate", "br_unemployment_ipea_rate"),
        transform="percent_to_decimal",
        description="Taxa de desemprego em decimal.",
        unit="decimal_rate",
    ),
    AnalyticsSeriesDefinition(
        output_name="selic_monthly_rate",
        series_candidates=("br_selic_bcb_monthly_rate",),
        transform="percent_to_decimal",
        description="Selic acumulada no mes em decimal.",
        unit="decimal_rate",
    ),
    AnalyticsSeriesDefinition(
        output_name="activity_level",
        series_candidates=("br_activity_ipea_monthly_gdp", "br_activity_sidra_industry_sa_index"),
        transform="identity",
        description="Proxy mensal de atividade economica.",
        unit="level",
    ),
    AnalyticsSeriesDefinition(
        output_name="activity_growth_12m",
        series_candidates=("br_activity_ipea_monthly_gdp", "br_activity_sidra_industry_sa_index"),
        transform="pct_change_12m",
        description="Crescimento em 12 meses da proxy de atividade.",
        unit="decimal_rate",
    ),
    AnalyticsSeriesDefinition(
        output_name="delinquency_total",
        series_candidates=("br_delinquency_bcb_total",),
        transform="percent_to_decimal",
        description="Inadimplencia agregada total em decimal.",
        unit="decimal_rate",
    ),
    AnalyticsSeriesDefinition(
        output_name="delinquency_pf_total",
        series_candidates=("br_delinquency_bcb_pf_total",),
        transform="percent_to_decimal",
        description="Inadimplencia agregada PF em decimal.",
        unit="decimal_rate",
    ),
    AnalyticsSeriesDefinition(
        output_name="delinquency_pj_total",
        series_candidates=("br_delinquency_bcb_pj_total",),
        transform="percent_to_decimal",
        description="Inadimplencia agregada PJ em decimal.",
        unit="decimal_rate",
    ),
    AnalyticsSeriesDefinition(
        output_name="credit_stock_total",
        series_candidates=("br_credit_stock_bcb_total",),
        transform="identity",
        description="Saldo agregado da carteira de credito total.",
        unit="level",
    ),
    AnalyticsSeriesDefinition(
        output_name="credit_stock_pf_total",
        series_candidates=("br_credit_stock_bcb_pf_total",),
        transform="identity",
        description="Saldo agregado da carteira de credito PF.",
        unit="level",
    ),
    AnalyticsSeriesDefinition(
        output_name="credit_stock_pj_total",
        series_candidates=("br_credit_stock_bcb_pj_total",),
        transform="identity",
        description="Saldo agregado da carteira de credito PJ.",
        unit="level",
    ),
    AnalyticsSeriesDefinition(
        output_name="spread_total",
        series_candidates=("br_credit_spread_bcb_total",),
        transform="percent_to_decimal",
        description="Spread agregado de credito total em decimal.",
        unit="decimal_rate",
    ),
    AnalyticsSeriesDefinition(
        output_name="spread_pf_total",
        series_candidates=("br_credit_spread_bcb_pf_total",),
        transform="percent_to_decimal",
        description="Spread agregado de credito PF em decimal.",
        unit="decimal_rate",
    ),
    AnalyticsSeriesDefinition(
        output_name="spread_pj_total",
        series_candidates=("br_credit_spread_bcb_pj_total",),
        transform="percent_to_decimal",
        description="Spread agregado de credito PJ em decimal.",
        unit="decimal_rate",
    ),
)


RELATIONSHIP_DEFINITIONS: tuple[RelationshipDefinition, ...] = (
    RelationshipDefinition(
        relationship_name="delinquency_vs_unemployment",
        driver="unemployment_rate",
        response="delinquency_total",
        description="Leitura descritiva entre desemprego e inadimplencia agregada.",
    ),
    RelationshipDefinition(
        relationship_name="spread_vs_selic",
        driver="selic_monthly_rate",
        response="spread_total",
        description="Leitura descritiva entre Selic mensal e spread agregado.",
    ),
    RelationshipDefinition(
        relationship_name="credit_growth_vs_activity",
        driver="activity_growth_12m",
        response="credit_stock_total_12m_growth",
        description="Leitura descritiva entre crescimento do credito e atividade.",
    ),
)


SUMMARY_COLUMNS: tuple[str, ...] = (
    "delinquency_total",
    "spread_total",
    "credit_stock_total",
    "credit_stock_total_12m_growth",
    "unemployment_rate",
    "selic_monthly_rate",
    "activity_growth_12m",
)

CORRELATION_COLUMNS: tuple[str, ...] = (
    "unemployment_rate",
    "selic_monthly_rate",
    "activity_growth_12m",
    "delinquency_total",
    "spread_total",
    "credit_stock_total_12m_growth",
)


def run_macro_credit_analysis(
    macro_wide_path: str | Path,
    *,
    max_ffill_months: int = 3,
    start: str | pd.Timestamp | None = None,
    end: str | pd.Timestamp | None = None,
    scenarios: dict[str, dict[str, float]] | None = None,
) -> MacroCreditAnalyticsResult:
    """Executa a camada de analytics agregada usando o feature store macro."""
    feature_store = MacroFeatureStore(
        macro_wide_path,
        max_ffill_months=max_ffill_months,
    )
    monthly_frame = feature_store.load_monthly(start=start, end=end)
    reference_frame, selected_series, unit_mapping = build_macro_credit_reference_frame(monthly_frame)
    analysis_frame = trim_to_core_analysis_window(reference_frame)

    reference_summary = build_reference_summary(
        analysis_frame,
        selected_series=selected_series,
        unit_mapping=unit_mapping,
    )
    relationship_summary = build_relationship_summary(analysis_frame)
    correlation_matrix = build_correlation_matrix(analysis_frame)
    scenario_calibration = build_scenario_calibration(
        analysis_frame,
        scenarios=scenarios or SCENARIOS,
    )
    observed_scenario_overlays = build_observed_scenario_overlay_table(
        analysis_frame,
        scenarios=scenarios or SCENARIOS,
    )
    validation_tables = build_validation_tables(analysis_frame)

    return MacroCreditAnalyticsResult(
        reference_frame=analysis_frame,
        selected_series=selected_series,
        reference_summary=reference_summary,
        relationship_summary=relationship_summary,
        correlation_matrix=correlation_matrix,
        scenario_calibration=scenario_calibration,
        observed_scenario_overlays=observed_scenario_overlays,
        validation_tables=validation_tables,
    )


def build_macro_credit_reference_frame(
    monthly_frame: pd.DataFrame,
    *,
    series_definitions: Sequence[AnalyticsSeriesDefinition] = ANALYTICS_SERIES_DEFINITIONS,
) -> tuple[pd.DataFrame, dict[str, str], dict[str, str]]:
    """Constroi a visao mensal agregada de macro e credito."""
    reference_frame = pd.DataFrame(index=monthly_frame.index.copy())
    selected_series: dict[str, str] = {}
    unit_mapping: dict[str, str] = {}

    for definition in series_definitions:
        transformed_series, selected_series_name = _resolve_series(monthly_frame, definition)
        if transformed_series is None or selected_series_name is None:
            continue

        reference_frame[definition.output_name] = transformed_series
        selected_series[definition.output_name] = selected_series_name
        unit_mapping[definition.output_name] = definition.unit

    positive_level_columns = [
        "activity_level",
        "credit_stock_total",
        "credit_stock_pf_total",
        "credit_stock_pj_total",
    ]
    for column in positive_level_columns:
        if column in reference_frame.columns:
            reference_frame[column] = reference_frame[column].where(reference_frame[column] > 0.0)

    if "credit_stock_total" in reference_frame.columns:
        credit_growth = reference_frame["credit_stock_total"].pct_change(periods=12, fill_method=None)
        reference_frame["credit_stock_total_12m_growth"] = credit_growth.replace([np.inf, -np.inf], np.nan)
        selected_series["credit_stock_total_12m_growth"] = selected_series["credit_stock_total"]
        unit_mapping["credit_stock_total_12m_growth"] = "decimal_rate"

    reference_frame.index.name = "date"
    return reference_frame.sort_index(), selected_series, unit_mapping


def build_reference_summary(
    reference_frame: pd.DataFrame,
    *,
    selected_series: dict[str, str],
    unit_mapping: dict[str, str],
) -> pd.DataFrame:
    """Resume niveis recentes, variacao em 12 meses e a serie usada em cada metrica."""
    summary_rows: list[dict[str, object]] = []

    for column in SUMMARY_COLUMNS:
        if column not in reference_frame.columns:
            continue

        series = reference_frame[column].dropna()
        if series.empty:
            continue

        latest_date = series.index.max()
        latest_value = float(series.loc[latest_date])
        lag_12m_value = series.shift(12).loc[latest_date] if latest_date in series.index else np.nan
        pct_change_12m = series.pct_change(periods=12, fill_method=None).loc[latest_date]

        summary_rows.append(
            {
                "metric": column,
                "source_series": selected_series.get(column),
                "unit": unit_mapping.get(column, "level"),
                "latest_date": latest_date,
                "latest_value": latest_value,
                "delta_12m": float(latest_value - lag_12m_value) if pd.notna(lag_12m_value) else np.nan,
                "pct_change_12m": float(pct_change_12m) if pd.notna(pct_change_12m) else np.nan,
                "min_value": float(series.min()),
                "max_value": float(series.max()),
            }
        )

    return pd.DataFrame(summary_rows)


def build_relationship_summary(reference_frame: pd.DataFrame) -> pd.DataFrame:
    """Calcula medidas descritivas simples entre pares macro-credito."""
    rows: list[dict[str, object]] = []

    for definition in RELATIONSHIP_DEFINITIONS:
        pair_frame = reference_frame[[definition.driver, definition.response]].dropna()
        if pair_frame.empty:
            continue

        driver_series = pair_frame[definition.driver]
        response_series = pair_frame[definition.response]
        driver_variance = float(driver_series.var(ddof=0))
        beta_like = np.nan

        if driver_variance > 0.0:
            covariance = float(np.cov(driver_series, response_series, ddof=0)[0, 1])
            beta_like = covariance / driver_variance

        rows.append(
            {
                "relationship_name": definition.relationship_name,
                "driver": definition.driver,
                "response": definition.response,
                "description": definition.description,
                "observations": len(pair_frame),
                "correlation": float(pair_frame.corr().iloc[0, 1]) if len(pair_frame) > 1 else np.nan,
                "beta_like_sensitivity": beta_like,
                "latest_driver_value": float(driver_series.iloc[-1]),
                "latest_response_value": float(response_series.iloc[-1]),
            }
        )

    return pd.DataFrame(rows)


def build_correlation_matrix(reference_frame: pd.DataFrame) -> pd.DataFrame:
    """Constroi uma matriz compacta de correlacoes entre macro e credito agregado."""
    available_columns = [column for column in CORRELATION_COLUMNS if column in reference_frame.columns]
    if not available_columns:
        return pd.DataFrame()

    correlation_frame = reference_frame[available_columns].dropna()
    if correlation_frame.empty:
        return pd.DataFrame(index=available_columns, columns=available_columns, dtype=float)

    return correlation_frame.corr()


def build_validation_tables(reference_frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Organiza as tabelas usadas para validacao macro externa."""
    validation_tables: dict[str, pd.DataFrame] = {
        "reference_frame": reference_frame.copy(),
    }

    validation_pairs = {
        "delinquency_vs_unemployment": [
            "delinquency_total",
            "delinquency_pf_total",
            "delinquency_pj_total",
            "unemployment_rate",
        ],
        "spread_vs_selic": [
            "spread_total",
            "spread_pf_total",
            "spread_pj_total",
            "selic_monthly_rate",
        ],
        "credit_vs_activity": [
            "credit_stock_total",
            "credit_stock_total_12m_growth",
            "activity_level",
            "activity_growth_12m",
        ],
    }

    for table_name, columns in validation_pairs.items():
        available_columns = [column for column in columns if column in reference_frame.columns]
        validation_tables[table_name] = reference_frame[available_columns].dropna(how="all")

    return validation_tables


def trim_to_core_analysis_window(reference_frame: pd.DataFrame) -> pd.DataFrame:
    """Recorta a janela para o periodo com cobertura minima dos pilares centrais."""
    core_columns = [
        "delinquency_total",
        "spread_total",
        "credit_stock_total",
        "unemployment_rate",
        "selic_monthly_rate",
        "activity_growth_12m",
    ]

    start_dates: list[pd.Timestamp] = []
    for column in core_columns:
        if column not in reference_frame.columns:
            continue

        valid_series = reference_frame[column].dropna()
        if valid_series.empty:
            continue

        start_dates.append(valid_series.index.min())

    if not start_dates:
        return reference_frame.copy()

    analysis_start = max(start_dates)
    return reference_frame.loc[analysis_start:].copy()


def build_scenario_calibration(
    reference_frame: pd.DataFrame,
    *,
    scenarios: dict[str, dict[str, float]],
) -> pd.DataFrame:
    """Compara amplitudes historicas observadas com os choques do projeto."""
    stress_windows = _build_stress_windows(reference_frame)
    stress_masks = stress_windows["masks"]
    baseline_mask = stress_windows["baseline_mask"]

    rows: list[dict[str, object]] = []
    scenario_variable_map = {
        "unemployment_rate": "unemployment_shift",
        "selic_monthly_rate": "selic_shift",
        "activity_growth_12m": "gdp_shift",
    }

    calibration_columns = [
        "unemployment_rate",
        "selic_monthly_rate",
        "activity_growth_12m",
        "delinquency_total",
        "spread_total",
        "credit_stock_total_12m_growth",
    ]

    for column in calibration_columns:
        if column not in reference_frame.columns:
            continue

        baseline_series = reference_frame.loc[baseline_mask, column].dropna()
        if baseline_series.empty:
            continue

        baseline_median = float(baseline_series.median())
        adverse_series = reference_frame.loc[stress_masks["adverse"], column].dropna()
        severe_series = reference_frame.loc[stress_masks["severe"], column].dropna()

        adverse_median = float(adverse_series.median()) if not adverse_series.empty else np.nan
        severe_median = float(severe_series.median()) if not severe_series.empty else np.nan

        adverse_shift = adverse_median - baseline_median if pd.notna(adverse_median) else np.nan
        severe_shift = severe_median - baseline_median if pd.notna(severe_median) else np.nan

        configured_key = scenario_variable_map.get(column)
        rows.append(
            {
                "metric": column,
                "baseline_median": baseline_median,
                "adverse_historical_median": adverse_median,
                "adverse_shift_vs_baseline": adverse_shift,
                "severe_historical_median": severe_median,
                "severe_shift_vs_baseline": severe_shift,
                "configured_adverse_shift": scenarios["adverse"].get(configured_key) if configured_key else np.nan,
                "configured_severe_shift": scenarios["severe"].get(configured_key) if configured_key else np.nan,
                "stress_window_definition": stress_windows["definition"],
            }
        )

    return pd.DataFrame(rows)


def build_observed_scenario_overlay_table(
    reference_frame: pd.DataFrame,
    *,
    scenarios: dict[str, dict[str, float]],
) -> pd.DataFrame:
    """Traduz a leitura historica em uma tabela opcional de calibracao de cenarios."""
    stress_windows = _build_stress_windows(reference_frame)
    baseline_mask = stress_windows["baseline_mask"]
    stress_masks = stress_windows["masks"]

    baseline = reference_frame.loc[baseline_mask]
    if baseline.empty:
        return pd.DataFrame()

    baseline_delinquency = _safe_median(baseline.get("delinquency_total"))
    baseline_spread = _safe_median(baseline.get("spread_total"))

    rows: list[dict[str, object]] = [
        {
            "scenario": "base",
            "observed_unemployment_shift": 0.0,
            "observed_selic_shift": 0.0,
            "observed_gdp_shift": 0.0,
            "delinquency_multiplier_proxy": 1.0,
            "spread_multiplier_proxy": 1.0,
            "configured_unemployment_shift": scenarios["base"]["unemployment_shift"],
            "configured_selic_shift": scenarios["base"]["selic_shift"],
            "configured_gdp_shift": scenarios["base"]["gdp_shift"],
            "configured_pd_multiplier": scenarios["base"]["pd_multiplier"],
            "configured_lgd_multiplier": scenarios["base"]["lgd_multiplier"],
            "stress_window_definition": stress_windows["definition"],
        }
    ]

    for scenario_name in ("adverse", "severe"):
        scenario_frame = reference_frame.loc[stress_masks[scenario_name]]
        if scenario_frame.empty:
            continue

        unemployment_shift = _safe_median(scenario_frame.get("unemployment_rate")) - _safe_median(
            baseline.get("unemployment_rate")
        )
        selic_shift = _safe_median(scenario_frame.get("selic_monthly_rate")) - _safe_median(
            baseline.get("selic_monthly_rate")
        )
        gdp_shift = _safe_median(scenario_frame.get("activity_growth_12m")) - _safe_median(
            baseline.get("activity_growth_12m")
        )

        delinquency_multiplier = np.nan
        spread_multiplier = np.nan
        scenario_delinquency = _safe_median(scenario_frame.get("delinquency_total"))
        scenario_spread = _safe_median(scenario_frame.get("spread_total"))

        if pd.notna(baseline_delinquency) and baseline_delinquency != 0.0 and pd.notna(scenario_delinquency):
            delinquency_multiplier = scenario_delinquency / baseline_delinquency
        if pd.notna(baseline_spread) and baseline_spread != 0.0 and pd.notna(scenario_spread):
            spread_multiplier = scenario_spread / baseline_spread

        rows.append(
            {
                "scenario": scenario_name,
                "observed_unemployment_shift": unemployment_shift,
                "observed_selic_shift": selic_shift,
                "observed_gdp_shift": gdp_shift,
                "delinquency_multiplier_proxy": delinquency_multiplier,
                "spread_multiplier_proxy": spread_multiplier,
                "configured_unemployment_shift": scenarios[scenario_name]["unemployment_shift"],
                "configured_selic_shift": scenarios[scenario_name]["selic_shift"],
                "configured_gdp_shift": scenarios[scenario_name]["gdp_shift"],
                "configured_pd_multiplier": scenarios[scenario_name]["pd_multiplier"],
                "configured_lgd_multiplier": scenarios[scenario_name]["lgd_multiplier"],
                "stress_window_definition": stress_windows["definition"],
            }
        )

    return pd.DataFrame(rows)


def _build_stress_windows(reference_frame: pd.DataFrame) -> dict[str, object]:
    delinquency_series = reference_frame.get("delinquency_total")
    if delinquency_series is None:
        raise ValueError("A serie 'delinquency_total' e obrigatoria para calibracao historica.")

    delinquency_series = delinquency_series.dropna()
    if delinquency_series.empty:
        raise ValueError("A serie 'delinquency_total' nao possui observacoes validas.")

    adverse_threshold = float(delinquency_series.quantile(0.75))
    severe_threshold = float(delinquency_series.quantile(0.90))

    adverse_mask = reference_frame["delinquency_total"] >= adverse_threshold
    severe_mask = reference_frame["delinquency_total"] >= severe_threshold
    baseline_mask = reference_frame["delinquency_total"].notna()

    return {
        "baseline_mask": baseline_mask,
        "masks": {
            "adverse": adverse_mask,
            "severe": severe_mask,
        },
        "definition": (
            "Historical stress windows defined by delinquency_total quantiles: "
            f"adverse >= p75 ({adverse_threshold:.4f}), severe >= p90 ({severe_threshold:.4f})"
        ),
    }


def _resolve_series(
    monthly_frame: pd.DataFrame,
    definition: AnalyticsSeriesDefinition,
) -> tuple[pd.Series | None, str | None]:
    for series_name in definition.series_candidates:
        if series_name not in monthly_frame.columns:
            continue

        transformed = _apply_transform(monthly_frame[series_name], definition.transform)
        if transformed.dropna().empty:
            continue

        return transformed.rename(definition.output_name), series_name

    return None, None


def _apply_transform(series: pd.Series, transform_name: str) -> pd.Series:
    numeric_series = pd.to_numeric(series, errors="coerce")

    if transform_name == "identity":
        return numeric_series
    if transform_name == "percent_to_decimal":
        return numeric_series / 100.0
    if transform_name == "pct_change_12m":
        return numeric_series.pct_change(periods=12, fill_method=None)

    raise ValueError(f"Transformacao nao suportada para analytics macro de credito: {transform_name}")


def _safe_median(series: pd.Series | None) -> float:
    if series is None:
        return np.nan

    clean_series = pd.Series(series).dropna()
    if clean_series.empty:
        return np.nan

    return float(clean_series.median())
