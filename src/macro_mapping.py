from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class MacroFactorMapping:
    """Define como um fator do motor deve ser obtido a partir do feature store."""

    factor_name: str
    series_candidates: tuple[str, ...]
    transform: str
    description: str


@dataclass(frozen=True)
class MacroFactorSnapshot:
    """Representa um snapshot unico dos fatores macro usados pelo motor."""

    reference_date: pd.Timestamp
    unemployment: float
    selic_proxy: float
    gdp_growth: float
    selected_series: dict[str, str]

    def as_dict(self) -> dict[str, float]:
        """Converte o snapshot para o formato esperado pelo gerador sintetico."""
        return {
            "unemployment": self.unemployment,
            "selic_proxy": self.selic_proxy,
            "gdp_growth": self.gdp_growth,
        }


MACRO_FACTOR_MAPPINGS: tuple[MacroFactorMapping, ...] = (
    MacroFactorMapping(
        factor_name="unemployment",
        series_candidates=(
            "br_unemployment_sidra_rate",
            "br_unemployment_ipea_rate",
        ),
        transform="percent_to_decimal",
        description="Taxa de desemprego em decimal; prioriza SIDRA e usa IPEA como fallback.",
    ),
    MacroFactorMapping(
        factor_name="selic_proxy",
        series_candidates=("br_selic_bcb_monthly_rate",),
        transform="percent_to_decimal",
        description="Selic acumulada no mes em decimal.",
    ),
    MacroFactorMapping(
        factor_name="gdp_growth",
        series_candidates=(
            "br_activity_ipea_monthly_gdp",
            "br_activity_sidra_industry_sa_index",
        ),
        transform="pct_change_12m",
        description="Proxy de crescimento em 12 meses; prioriza PIB mensal do IPEA e usa producao industrial como fallback.",
    ),
)


def build_model_macro_frame(
    monthly_frame: pd.DataFrame,
    *,
    mappings: tuple[MacroFactorMapping, ...] = MACRO_FACTOR_MAPPINGS,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Constroi o DataFrame de fatores do motor a partir do feature store mensal."""
    factors = pd.DataFrame(index=monthly_frame.index.copy())
    selected_series: dict[str, str] = {}
    missing_factors: list[str] = []

    for mapping in mappings:
        transformed_series, source_series = _resolve_factor_series(monthly_frame, mapping)
        if transformed_series is None or source_series is None:
            missing_factors.append(mapping.factor_name)
            continue

        factors[mapping.factor_name] = transformed_series
        selected_series[mapping.factor_name] = source_series

    if missing_factors:
        raise ValueError(
            "Nao foi possivel construir todos os fatores macro do motor. "
            f"Fatores ausentes: {', '.join(missing_factors)}"
        )

    return factors.sort_index(), selected_series


def resolve_macro_snapshot(
    factor_frame: pd.DataFrame,
    *,
    selected_series: dict[str, str],
    reference_date: str | pd.Timestamp | None = None,
) -> MacroFactorSnapshot:
    """Resolve um unico snapshot dos fatores macro para a data de referencia."""
    if factor_frame.empty:
        raise ValueError("O DataFrame de fatores macro esta vazio.")

    normalized_reference_date = _normalize_reference_date(reference_date)
    if normalized_reference_date is None:
        candidate_rows = factor_frame.dropna()
    else:
        candidate_rows = factor_frame.loc[:normalized_reference_date].dropna()

    if candidate_rows.empty:
        raise ValueError("Nao ha fatores macro completos para a data de referencia informada.")

    resolved_date = candidate_rows.index.max()
    row = candidate_rows.loc[resolved_date]

    return MacroFactorSnapshot(
        reference_date=resolved_date,
        unemployment=float(row["unemployment"]),
        selic_proxy=float(row["selic_proxy"]),
        gdp_growth=float(row["gdp_growth"]),
        selected_series=dict(selected_series),
    )


def _resolve_factor_series(
    monthly_frame: pd.DataFrame,
    mapping: MacroFactorMapping,
) -> tuple[pd.Series | None, str | None]:
    for series_name in mapping.series_candidates:
        if series_name not in monthly_frame.columns:
            continue

        transformed = _apply_transform(monthly_frame[series_name], mapping.transform)
        if transformed.dropna().empty:
            continue

        return transformed.rename(mapping.factor_name), series_name

    return None, None


def _apply_transform(series: pd.Series, transform_name: str) -> pd.Series:
    numeric_series = pd.to_numeric(series, errors="coerce")

    if transform_name == "percent_to_decimal":
        return numeric_series / 100.0

    if transform_name == "pct_change_12m":
        return numeric_series.pct_change(periods=12, fill_method=None)

    raise ValueError(f"Transformacao macro nao suportada: {transform_name}")


def _normalize_reference_date(
    reference_date: str | pd.Timestamp | None,
) -> pd.Timestamp | None:
    if reference_date is None:
        return None

    return pd.to_datetime(reference_date, errors="raise") + pd.offsets.MonthEnd(0)
