from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


MacroSource = Literal["ipea", "sidra", "bcb"]


@dataclass(frozen=True)
class MacroSeriesDefinition:
    """Define uma serie macroeconomica disponivel para o pipeline."""

    series_code: str
    series_name: str
    source: MacroSource
    topic: str
    enabled: bool = True
    provider_code: str | None = None
    request_url: str | None = None
    filters: tuple[str, ...] = ()
    start: str | None = None
    end: str | None = None
    notes: str | None = None


# TODO: revisar se a fase seguinte vai manter apenas Brasil total ou se ja devemos
# abrir recortes regionais e classificacoes adicionais no catalogo.
# TODO: avaliar a inclusao da Meta Selic diaria depois que definirmos a estrategia
# de agregacao mensal e a janela padrao para series diarias do BCB.
MACRO_SERIES_CATALOG: tuple[MacroSeriesDefinition, ...] = (
    MacroSeriesDefinition(
        series_code="br_ipca_ipea_index",
        series_name="IPCA geral - indice",
        source="ipea",
        topic="inflation",
        provider_code="PRECOS12_IPCA12",
    ),
    MacroSeriesDefinition(
        series_code="br_ipca_ipea_mom",
        series_name="IPCA geral - variacao mensal",
        source="ipea",
        topic="inflation",
        provider_code="PRECOS12_IPCAG12",
    ),
    MacroSeriesDefinition(
        series_code="br_unemployment_ipea_rate",
        series_name="Taxa de desocupacao - PNAD Continua",
        source="ipea",
        topic="unemployment",
        provider_code="PNADC12_TDESOC12",
    ),
    MacroSeriesDefinition(
        series_code="br_activity_ipea_monthly_gdp",
        series_name="PIB mensal",
        source="ipea",
        topic="activity",
        provider_code="BM12_PIB12",
        notes="Proxy mensal publicada pelo IPEA a partir de fonte Bacen.",
    ),
    MacroSeriesDefinition(
        series_code="br_ipca_sidra_mom",
        series_name="IPCA geral - variacao mensal",
        source="sidra",
        topic="inflation",
        provider_code="1737",
        request_url="https://apisidra.ibge.gov.br/values/t/1737/n1/all/p/all/v/63/h/y/f/a",
    ),
    MacroSeriesDefinition(
        series_code="br_unemployment_sidra_rate",
        series_name="Taxa de desocupacao - PNAD Continua mensal",
        source="sidra",
        topic="unemployment",
        provider_code="6381",
        request_url="https://apisidra.ibge.gov.br/values/t/6381/n1/all/p/all/v/4099/h/y/f/a",
    ),
    MacroSeriesDefinition(
        series_code="br_activity_sidra_industry_sa_index",
        series_name="Producao fisica industrial - indice com ajuste sazonal",
        source="sidra",
        topic="activity",
        provider_code="8888",
        request_url="https://apisidra.ibge.gov.br/values/t/8888/n1/all/p/all/v/12607/c544/129314/h/y/f/a",
    ),
    MacroSeriesDefinition(
        series_code="br_selic_bcb_monthly_rate",
        series_name="Taxa Selic acumulada no mes",
        source="bcb",
        topic="interest_rate",
        provider_code="4390",
    ),
    MacroSeriesDefinition(
        series_code="br_credit_stock_bcb_total",
        series_name="Saldo da carteira de credito - total",
        source="bcb",
        topic="credit_balance",
        provider_code="20539",
    ),
    MacroSeriesDefinition(
        series_code="br_credit_stock_bcb_pj_total",
        series_name="Saldo da carteira de credito - pessoas juridicas - total",
        source="bcb",
        topic="credit_balance",
        provider_code="20540",
    ),
    MacroSeriesDefinition(
        series_code="br_credit_stock_bcb_pf_total",
        series_name="Saldo da carteira de credito - pessoas fisicas - total",
        source="bcb",
        topic="credit_balance",
        provider_code="20541",
    ),
    MacroSeriesDefinition(
        series_code="br_delinquency_bcb_total",
        series_name="Inadimplencia da carteira de credito - total",
        source="bcb",
        topic="delinquency",
        provider_code="21082",
    ),
    MacroSeriesDefinition(
        series_code="br_delinquency_bcb_pj_total",
        series_name="Inadimplencia da carteira de credito - pessoas juridicas - total",
        source="bcb",
        topic="delinquency",
        provider_code="21083",
    ),
    MacroSeriesDefinition(
        series_code="br_delinquency_bcb_pf_total",
        series_name="Inadimplencia da carteira de credito - pessoas fisicas - total",
        source="bcb",
        topic="delinquency",
        provider_code="21084",
    ),
    MacroSeriesDefinition(
        series_code="br_credit_spread_bcb_total",
        series_name="Spread medio das operacoes de credito - total",
        source="bcb",
        topic="credit_spread",
        provider_code="20783",
    ),
    MacroSeriesDefinition(
        series_code="br_credit_spread_bcb_pj_total",
        series_name="Spread medio das operacoes de credito - pessoas juridicas - total",
        source="bcb",
        topic="credit_spread",
        provider_code="20784",
    ),
    MacroSeriesDefinition(
        series_code="br_credit_spread_bcb_pf_total",
        series_name="Spread medio das operacoes de credito - pessoas fisicas - total",
        source="bcb",
        topic="credit_spread",
        provider_code="20785",
    ),
)
