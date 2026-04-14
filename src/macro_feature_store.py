from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.macro_mapping import MacroFactorSnapshot, build_model_macro_frame, resolve_macro_snapshot


class MacroFeatureStore:
    """Le e harmoniza os fatores macroeconomicos processados para uso no motor."""

    def __init__(
        self,
        path: str | Path,
        *,
        max_ffill_months: int = 3,
    ) -> None:
        self.path = Path(path)
        self.max_ffill_months = max_ffill_months

    def load_raw(self) -> pd.DataFrame:
        """Le o arquivo wide processado e devolve um DataFrame indexado por data."""
        if not self.path.exists():
            raise FileNotFoundError(f"Arquivo macro nao encontrado: {self.path}")

        frame = pd.read_csv(self.path)
        if "date" not in frame.columns:
            raise ValueError("O arquivo macro wide precisa conter uma coluna 'date'.")

        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame = frame.dropna(subset=["date"]).sort_values("date")

        value_columns = [column for column in frame.columns if column != "date"]
        for column in value_columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

        return frame.set_index("date").sort_index()

    def load_monthly(
        self,
        *,
        start: str | pd.Timestamp | None = None,
        end: str | pd.Timestamp | None = None,
    ) -> pd.DataFrame:
        """Harmoniza o arquivo wide para um indice mensal unico."""
        frame = self.load_raw().copy()
        frame.index = pd.to_datetime(frame.index, errors="coerce") + pd.offsets.MonthEnd(0)
        frame = frame.groupby(level=0).last().sort_index()

        if not frame.empty:
            full_month_index = pd.date_range(
                start=frame.index.min(),
                end=frame.index.max(),
                freq="ME",
            )
            frame = frame.reindex(full_month_index)
            if self.max_ffill_months > 0:
                frame = frame.ffill(limit=self.max_ffill_months)

        frame.index.name = "date"

        if start is not None:
            frame = frame.loc[self._normalize_month_date(start):]
        if end is not None:
            frame = frame.loc[: self._normalize_month_date(end)]

        return frame

    def get_model_factor_frame(
        self,
        *,
        start: str | pd.Timestamp | None = None,
        end: str | pd.Timestamp | None = None,
    ) -> pd.DataFrame:
        """Retorna a serie mensal dos fatores do motor ja mapeados."""
        monthly_frame = self.load_monthly(start=start, end=end)
        factor_frame, _ = build_model_macro_frame(monthly_frame)
        return factor_frame

    def get_model_macro_snapshot(
        self,
        *,
        reference_date: str | pd.Timestamp | None = None,
    ) -> MacroFactorSnapshot:
        """Resolve um snapshot unico dos fatores do motor para uma data de referencia."""
        monthly_frame = self.load_monthly()
        factor_frame, selected_series = build_model_macro_frame(monthly_frame)
        return resolve_macro_snapshot(
            factor_frame,
            selected_series=selected_series,
            reference_date=reference_date,
        )

    @staticmethod
    def _normalize_month_date(value: str | pd.Timestamp) -> pd.Timestamp:
        return pd.to_datetime(value, errors="raise") + pd.offsets.MonthEnd(0)
