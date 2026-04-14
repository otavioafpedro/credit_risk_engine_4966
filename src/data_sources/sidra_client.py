from __future__ import annotations

import re
import time
import unicodedata
from typing import Any, Mapping, Sequence

import pandas as pd
import requests


class SidraClient:
    """Cliente simples e resiliente para consultas do SIDRA/IBGE."""

    STATIC_RENAME_MAP: dict[str, str] = {
        "V": "value",
        "MN": "unit_name",
        "MC": "unit_code",
        "NN": "territorial_level_name",
        "NC": "territorial_level_code",
    }
    MONTH_ALIASES: dict[str, int] = {
        "jan": 1,
        "janeiro": 1,
        "fev": 2,
        "fevereiro": 2,
        "mar": 3,
        "marco": 3,
        "abr": 4,
        "abril": 4,
        "mai": 5,
        "maio": 5,
        "jun": 6,
        "junho": 6,
        "jul": 7,
        "julho": 7,
        "ago": 8,
        "agosto": 8,
        "set": 9,
        "setembro": 9,
        "out": 10,
        "outubro": 10,
        "nov": 11,
        "novembro": 11,
        "dez": 12,
        "dezembro": 12,
    }

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

    def fetch_by_url(
        self,
        url: str,
        *,
        rename: bool = True,
        clean: bool = True,
        extra_rename: Mapping[str, str] | None = None,
    ) -> pd.DataFrame:
        """Baixa uma consulta do SIDRA a partir de uma URL completa."""
        payload = self._request_json(url)
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"Resposta vazia ou invalida recebida do SIDRA para a URL: {url}")

        header = payload[0]
        rows = payload[1:]
        if not rows:
            raise ValueError(f"A consulta SIDRA nao retornou linhas de dados para a URL: {url}")

        frame = pd.DataFrame(rows)
        if rename:
            rename_map = self.STATIC_RENAME_MAP.copy()
            if extra_rename:
                rename_map.update(extra_rename)

            valid_rename = {column: target for column, target in rename_map.items() if column in frame.columns}
            frame = frame.rename(columns=valid_rename)

        if clean:
            frame = self._clean_df(frame)

        frame.attrs["sidra_header"] = header
        frame.attrs["source_url"] = url
        return frame

    def get_series(
        self,
        url: str,
        *,
        filters: Sequence[str] | None = None,
        start: str | None = None,
        end: str | None = None,
        value_col_name: str = "value",
    ) -> pd.DataFrame:
        """Baixa uma serie do SIDRA e devolve um DataFrame com indice de data e valor."""
        frame = self.fetch_by_url(url, rename=True, clean=True)
        filtered = self._filter_rows(frame, filters=filters)

        period_code_column, period_label_column = self._identify_period_columns(filtered)
        filtered["date"] = filtered.apply(
            lambda row: self._parse_period_value(
                row.get(period_code_column) if period_code_column else None,
                row.get(period_label_column) if period_label_column else None,
            ),
            axis=1,
        )
        filtered = filtered.dropna(subset=["date", "value"])

        if filtered.empty:
            raise ValueError("A consulta SIDRA nao retornou linhas validas apos o parsing de data.")

        series_frame = filtered[["date", "value"]].sort_values("date")
        if series_frame["date"].duplicated().any():
            raise ValueError(
                "A consulta SIDRA retornou mais de um valor por data. "
                "Refine os filtros da serie antes de consolidar o resultado."
            )

        series_frame = series_frame.set_index("date").rename(columns={"value": value_col_name})
        series_frame.index.name = "date"

        if start:
            series_frame = series_frame.loc[pd.to_datetime(start):]
        if end:
            series_frame = series_frame.loc[: pd.to_datetime(end)]

        return series_frame[[value_col_name]].copy()

    def _request_json(self, url: str) -> list[dict[str, Any]]:
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout_seconds)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, list):
                    raise ValueError("O SIDRA retornou um payload que nao e uma lista JSON.")
                return payload
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(self.retry_delay_seconds)

        raise RuntimeError(f"Falha ao consultar o SIDRA: {url}") from last_error

    def _clean_df(self, frame: pd.DataFrame) -> pd.DataFrame:
        cleaned = frame.copy()

        if "value" not in cleaned.columns:
            return cleaned

        cleaned["value"] = cleaned["value"].map(self._parse_numeric_value)
        cleaned = cleaned.dropna(subset=["value"])
        return cleaned

    def _filter_rows(self, frame: pd.DataFrame, filters: Sequence[str] | None = None) -> pd.DataFrame:
        if not filters:
            return frame.copy()

        filtered = frame.copy()
        text_columns = [
            column
            for column in filtered.columns
            if filtered[column].dtype == "object" and column != "value"
        ]

        if not text_columns:
            raise ValueError("A resposta do SIDRA nao contem colunas textuais para aplicar filtros.")

        normalized_text = filtered[text_columns].fillna("").astype(str).agg(" ".join, axis=1).map(self._normalize_text)

        for token in filters:
            filtered = filtered.loc[normalized_text.str.contains(self._normalize_text(token), regex=False)]
            normalized_text = normalized_text.loc[filtered.index]

        if filtered.empty:
            raise ValueError(
                "Nenhuma linha do SIDRA correspondeu aos filtros informados: "
                f"{', '.join(filters)}"
            )

        return filtered

    def _identify_period_columns(self, frame: pd.DataFrame) -> tuple[str | None, str | None]:
        label_candidates = [column for column in frame.columns if re.fullmatch(r"D\d+N", column)]
        best_candidate: tuple[float, str | None, str | None] | None = None

        for label_column in label_candidates:
            labels = frame[label_column].dropna().astype(str)
            if labels.empty:
                continue

            normalized_labels = labels.map(self._normalize_text)
            has_year_ratio = normalized_labels.str.contains(r"(?:19|20)\d{2}", regex=True).mean()
            has_month_ratio = normalized_labels.str.contains(
                r"jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez|trimestre",
                regex=True,
            ).mean()
            code_column = label_column[:-1] + "C"
            code_ratio = 0.0

            if code_column in frame.columns:
                codes = frame[code_column].dropna().astype(str).str.strip()
                if not codes.empty:
                    code_ratio = codes.str.fullmatch(r"\d{4}|\d{6}").mean()

            score = (2.0 * has_month_ratio) + has_year_ratio + code_ratio
            if best_candidate is None or score > best_candidate[0]:
                best_candidate = (
                    score,
                    code_column if code_column in frame.columns else None,
                    label_column,
                )

        if best_candidate is not None and best_candidate[0] >= 1.25:
            return best_candidate[1], best_candidate[2]

        code_candidates = [column for column in frame.columns if re.fullmatch(r"D\d+C", column)]
        for code_column in code_candidates:
            codes = frame[code_column].dropna().astype(str).str.strip()
            if codes.empty:
                continue

            matches_period_code = codes.str.fullmatch(r"\d{4}|\d{6}").mean()
            if matches_period_code >= 0.8:
                label_column = code_column[:-1] + "N"
                return (
                    code_column,
                    label_column if label_column in frame.columns else None,
                )

        raise ValueError(
            "Nao foi possivel identificar as colunas de periodo retornadas pelo SIDRA. "
            f"Colunas disponiveis: {list(frame.columns)}"
        )

    def _parse_period_value(
        self,
        period_code: Any | None,
        period_label: Any | None,
    ) -> pd.Timestamp | pd.NaT:
        parsed_from_label = self._parse_period_label(period_label)
        if pd.notna(parsed_from_label):
            return parsed_from_label

        return self._parse_period_code(period_code)

    def _parse_period_label(self, period_label: Any | None) -> pd.Timestamp | pd.NaT:
        if period_label is None or pd.isna(period_label):
            return pd.NaT

        normalized = self._normalize_text(str(period_label))
        year_match = re.search(r"(?:19|20)\d{2}", normalized)
        if not year_match:
            return pd.NaT

        year = int(year_match.group(0))
        month_tokens = re.findall(
            r"jan(?:eiro)?|fev(?:ereiro)?|mar(?:co)?|abr(?:il)?|mai(?:o)?|jun(?:ho)?|"
            r"jul(?:ho)?|ago(?:sto)?|set(?:embro)?|out(?:ubro)?|nov(?:embro)?|dez(?:embro)?",
            normalized,
        )
        if month_tokens:
            month = self.MONTH_ALIASES[month_tokens[-1]]
            return pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)

        quarter_match = re.search(r"(\d).{0,2}trimestre", normalized)
        if quarter_match:
            quarter = int(quarter_match.group(1))
            month = quarter * 3
            return pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)

        if re.fullmatch(r"\d{4}", str(period_label).strip()):
            return pd.Timestamp(year=year, month=12, day=31)

        return pd.NaT

    @staticmethod
    def _parse_period_code(period_code: Any | None) -> pd.Timestamp | pd.NaT:
        if period_code is None or pd.isna(period_code):
            return pd.NaT

        code = str(period_code).strip()
        if re.fullmatch(r"\d{6}", code):
            year = int(code[:4])
            sequence = int(code[4:])
            if 1 <= sequence <= 12:
                return pd.Timestamp(year=year, month=sequence, day=1) + pd.offsets.MonthEnd(0)
            if 1 <= sequence <= 4:
                return pd.Timestamp(year=year, month=sequence * 3, day=1) + pd.offsets.MonthEnd(0)

        if re.fullmatch(r"\d{4}", code):
            return pd.Timestamp(year=int(code), month=12, day=31)

        return pd.NaT

    @staticmethod
    def _parse_numeric_value(raw_value: Any) -> float | None:
        if raw_value is None or pd.isna(raw_value):
            return None

        text = str(raw_value).strip().replace("\u00a0", "")
        if text in {"", "...", "..", "X", "x"}:
            return None

        if re.fullmatch(r"[A-WYZ]", text):
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

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        normalized = "".join(character for character in normalized if not unicodedata.combining(character))
        return normalized.casefold().strip()
