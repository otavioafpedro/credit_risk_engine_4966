from __future__ import annotations

import time
from typing import Any

import pandas as pd
import requests


class BCBClient:
    """Cliente para series publicas do Banco Central via BCData/SGS."""

    BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"

    def __init__(
        self,
        session: requests.Session | None = None,
        *,
        timeout_seconds: float = 15.0,
        max_retries: int = 2,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

    def get_series(
        self,
        code: str | int,
        *,
        start: str | None = None,
        end: str | None = None,
        value_col_name: str = "value",
    ) -> pd.DataFrame:
        """Baixa uma serie temporal do BCB e devolve um DataFrame padronizado."""
        payload = self._request_json(code=code, start=start, end=end)
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"O BCB nao retornou dados para a serie {code}.")

        frame = pd.DataFrame(payload)
        if not {"data", "valor"}.issubset(frame.columns):
            raise ValueError(
                "A resposta do BCB nao contem as colunas esperadas 'data' e 'valor'. "
                f"Colunas disponiveis: {list(frame.columns)}"
            )

        frame["date"] = self._parse_date_column(frame["data"])
        frame["value"] = frame["valor"].map(self._parse_numeric_value)
        frame = frame.dropna(subset=["date", "value"])

        if frame.empty:
            raise ValueError(f"A serie {code} retornou apenas valores invalidos ou vazios.")

        series_frame = frame[["date", "value"]].sort_values("date").set_index("date")
        series_frame.index.name = "date"
        series_frame = series_frame.rename(columns={"value": value_col_name})

        return series_frame[[value_col_name]].copy()

    def _request_json(
        self,
        *,
        code: str | int,
        start: str | None = None,
        end: str | None = None,
    ) -> list[dict[str, Any]]:
        url = self._build_url(code=code, start=start, end=end)
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout_seconds)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, list):
                    raise ValueError("O BCB retornou um payload que nao e uma lista JSON.")
                return payload
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(self.retry_delay_seconds)

        raise RuntimeError(f"Falha ao consultar a serie BCB {code}. URL: {url}") from last_error

    def _build_url(
        self,
        *,
        code: str | int,
        start: str | None = None,
        end: str | None = None,
    ) -> str:
        params = ["formato=json"]

        if start:
            params.append(f"dataInicial={self._format_bcb_date(start)}")
        if end:
            params.append(f"dataFinal={self._format_bcb_date(end)}")

        query_string = "&".join(params)
        return f"{self.BASE_URL.format(code=code)}?{query_string}"

    @staticmethod
    def _format_bcb_date(value: str) -> str:
        return pd.to_datetime(value, errors="raise").strftime("%d/%m/%Y")

    @staticmethod
    def _parse_date_column(raw_dates: pd.Series) -> pd.Series:
        parsed = pd.to_datetime(raw_dates.astype(str).str.strip(), format="%d/%m/%Y", errors="coerce")
        if parsed.notna().any():
            return parsed

        return pd.to_datetime(raw_dates.astype(str).str.strip(), dayfirst=True, errors="coerce")

    @staticmethod
    def _parse_numeric_value(raw_value: Any) -> float | None:
        if raw_value is None or pd.isna(raw_value):
            return None

        text = str(raw_value).strip().replace("\u00a0", "")
        if text in {"", "...", "..", "null", "None"}:
            return None

        if "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        elif "," in text:
            text = text.replace(".", "").replace(",", ".")

        try:
            return float(text)
        except ValueError:
            return None
