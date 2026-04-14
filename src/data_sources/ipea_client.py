from __future__ import annotations

from typing import Any

import pandas as pd

try:
    import ipeadatapy as ip
except ImportError:
    ip = None


class IpeaDataClient:
    """Cliente para consulta de series temporais do IPEA."""

    def __init__(self) -> None:
        self._series_cache: pd.DataFrame | None = None

    def list_series(self, refresh: bool = False) -> pd.DataFrame:
        """Retorna o catalogo completo de series disponivel no IPEA."""
        self._require_library()

        if self._series_cache is None or refresh:
            self._series_cache = ip.list_series()

        return self._series_cache.copy()

    def search_series(
        self,
        pattern: str,
        *,
        case: bool = False,
        regex: bool = False,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Filtra o catalogo do IPEA por nome da serie."""
        series_catalog = self.list_series()
        name_column = self._resolve_name_column(series_catalog)

        mask = series_catalog[name_column].astype(str).str.contains(
            pattern,
            case=case,
            na=False,
            regex=regex,
        )
        filtered = series_catalog.loc[mask].copy()

        if limit is not None:
            filtered = filtered.head(limit)

        return filtered

    def get_metadata(self, code: str) -> dict[str, Any]:
        """Retorna o metadata bruto da serie informada."""
        self._require_library()

        metadata = ip.metadata(code)
        if isinstance(metadata, dict):
            return metadata

        if hasattr(metadata, "items"):
            return dict(metadata)

        return {"raw_metadata": metadata}

    def get_series(
        self,
        code: str,
        *,
        start: str | None = None,
        end: str | None = None,
        value_col_name: str = "value",
    ) -> pd.DataFrame:
        """Baixa uma serie do IPEA com indice de data e coluna numerica de valor."""
        self._require_library()

        raw_series = ip.timeseries(code).copy()
        value_column = self._resolve_value_column(raw_series, code)

        raw_series["date"] = self._build_date_column(raw_series)
        raw_series[value_column] = pd.to_numeric(raw_series[value_column], errors="coerce")

        cleaned = (
            raw_series.dropna(subset=["date", value_column])
            .set_index("date")
            .sort_index()
            .rename(columns={value_column: value_col_name})
        )
        cleaned.index.name = "date"

        if start:
            cleaned = cleaned.loc[pd.to_datetime(start):]
        if end:
            cleaned = cleaned.loc[: pd.to_datetime(end)]

        return cleaned[[value_col_name]].copy()

    @staticmethod
    def _resolve_name_column(series_catalog: pd.DataFrame) -> str:
        for column in series_catalog.columns:
            if column.upper() == "NAME":
                return column

        raise ValueError("O catalogo do IPEA nao contem uma coluna NAME.")

    @staticmethod
    def _resolve_value_column(series_frame: pd.DataFrame, code: str) -> str:
        value_columns = [column for column in series_frame.columns if column.upper().startswith("VALUE")]
        if not value_columns:
            raise ValueError(
                f"Nenhuma coluna VALUE foi encontrada para a série {code}. "
                f"Colunas disponiveis: {list(series_frame.columns)}"
            )

        return value_columns[0]

    @staticmethod
    def _build_date_column(series_frame: pd.DataFrame) -> pd.Series:
        if {"YEAR", "MONTH", "DAY"}.issubset(series_frame.columns):
            return pd.to_datetime(
                {
                    "year": pd.to_numeric(series_frame["YEAR"], errors="coerce"),
                    "month": pd.to_numeric(series_frame["MONTH"], errors="coerce").fillna(1),
                    "day": pd.to_numeric(series_frame["DAY"], errors="coerce").fillna(1),
                },
                errors="coerce",
            )

        if {"YEAR", "MONTH"}.issubset(series_frame.columns):
            return pd.to_datetime(
                {
                    "year": pd.to_numeric(series_frame["YEAR"], errors="coerce"),
                    "month": pd.to_numeric(series_frame["MONTH"], errors="coerce").fillna(1),
                    "day": 1,
                },
                errors="coerce",
            )

        if "DATE" in series_frame.columns:
            return pd.to_datetime(series_frame["DATE"], errors="coerce")

        raise ValueError(
            "Nao foi possivel identificar as colunas de data retornadas pelo IPEA. "
            f"Colunas disponiveis: {list(series_frame.columns)}"
        )

    @staticmethod
    def _require_library() -> None:
        if ip is None:
            raise ImportError(
                "A dependência 'ipeadatapy' não está instalada. "
                "Adicione o pacote ao ambiente antes de usar o cliente do IPEA."
            )
