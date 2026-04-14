from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Sequence

import pandas as pd

from src.data_sources.bcb_client import BCBClient
from src.data_sources.ipea_client import IpeaDataClient
from src.data_sources.sidra_client import SidraClient
from src.macro_series_catalog import MACRO_SERIES_CATALOG, MacroSeriesDefinition


DEFAULT_MACRO_EXPORT_PATH = Path("data/processed/macro_factors_raw.csv")
DEFAULT_MACRO_WIDE_EXPORT_PATH = Path("data/processed/macro_factors_wide.csv")
PIPELINE_COLUMNS = ["date", "source", "series_code", "series_name", "value"]
LoadStatus = Literal["success", "failed", "skipped"]


@dataclass(frozen=True)
class MacroLoadRecord:
    """Representa o resultado da carga de uma serie do catalogo."""

    series_code: str
    series_name: str
    source: str
    status: LoadStatus
    row_count: int = 0
    error: str | None = None


@dataclass(frozen=True)
class MacroPipelineResult:
    """Representa o resultado consolidado da execucao do pipeline."""

    data: pd.DataFrame
    loads: list[MacroLoadRecord] = field(default_factory=list)
    export_path: Path | None = None
    wide_export_path: Path | None = None

    @property
    def succeeded(self) -> list[MacroLoadRecord]:
        return [record for record in self.loads if record.status == "success"]

    @property
    def failed(self) -> list[MacroLoadRecord]:
        return [record for record in self.loads if record.status == "failed"]

    @property
    def skipped(self) -> list[MacroLoadRecord]:
        return [record for record in self.loads if record.status == "skipped"]

    def summarize_by_source(self) -> pd.DataFrame:
        """Resume o resultado da carga por origem."""
        if not self.loads:
            return pd.DataFrame(
                columns=["source", "series_loaded", "series_failed", "series_skipped", "row_count"]
            )

        summary_rows: list[dict[str, int | str]] = []
        sources = sorted({record.source for record in self.loads})

        for source in sources:
            source_records = [record for record in self.loads if record.source == source]
            summary_rows.append(
                {
                    "source": source,
                    "series_loaded": sum(record.status == "success" for record in source_records),
                    "series_failed": sum(record.status == "failed" for record in source_records),
                    "series_skipped": sum(record.status == "skipped" for record in source_records),
                    "row_count": sum(record.row_count for record in source_records),
                }
            )

        return pd.DataFrame(summary_rows)


class MacroDataPipeline:
    """Orquestra a ingestao e consolidacao das series macroeconomicas."""

    def __init__(
        self,
        bcb_client: BCBClient | None = None,
        ipea_client: IpeaDataClient | None = None,
        sidra_client: SidraClient | None = None,
        catalog: Sequence[MacroSeriesDefinition] | None = None,
    ) -> None:
        self.bcb_client = bcb_client or BCBClient()
        self.ipea_client = ipea_client or IpeaDataClient()
        self.sidra_client = sidra_client or SidraClient()
        self.catalog = tuple(catalog or MACRO_SERIES_CATALOG)

    def run(
        self,
        *,
        export_path: str | Path | None = None,
        wide_export_path: str | Path | None = None,
        catalog: Sequence[MacroSeriesDefinition] | None = None,
    ) -> MacroPipelineResult:
        """Executa o pipeline e consolida as series disponiveis em um unico DataFrame."""
        selected_catalog = tuple(catalog or self.catalog)
        frames: list[pd.DataFrame] = []
        loads: list[MacroLoadRecord] = []

        for definition in selected_catalog:
            if not definition.enabled:
                loads.append(
                    MacroLoadRecord(
                        series_code=definition.series_code,
                        series_name=definition.series_name,
                        source=definition.source,
                        status="skipped",
                    )
                )
                continue

            try:
                series_frame = self._load_series(definition)
                standardized = self._standardize_series(definition, series_frame)
                frames.append(standardized)
                loads.append(
                    MacroLoadRecord(
                        series_code=definition.series_code,
                        series_name=definition.series_name,
                        source=definition.source,
                        status="success",
                        row_count=len(standardized),
                    )
                )
            except Exception as exc:
                loads.append(
                    MacroLoadRecord(
                        series_code=definition.series_code,
                        series_name=definition.series_name,
                        source=definition.source,
                        status="failed",
                        error=str(exc),
                    )
                )

        consolidated = self._combine_frames(frames)
        resolved_export_path: Path | None = None
        resolved_wide_export_path: Path | None = None

        if export_path is not None:
            resolved_export_path = self.export(consolidated, export_path)
        if wide_export_path is not None:
            wide_frame = self.to_wide(consolidated)
            resolved_wide_export_path = self.export_wide(wide_frame, wide_export_path)

        return MacroPipelineResult(
            data=consolidated,
            loads=loads,
            export_path=resolved_export_path,
            wide_export_path=resolved_wide_export_path,
        )

    def export(self, frame: pd.DataFrame, path: str | Path = DEFAULT_MACRO_EXPORT_PATH) -> Path:
        """Exporta o DataFrame consolidado para CSV."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output_path, index=False, date_format="%Y-%m-%d")
        return output_path

    def export_wide(self, frame: pd.DataFrame, path: str | Path = DEFAULT_MACRO_WIDE_EXPORT_PATH) -> Path:
        """Exporta o DataFrame pivotado para CSV."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output_path, index=True, date_format="%Y-%m-%d")
        return output_path

    def _load_series(self, definition: MacroSeriesDefinition) -> pd.DataFrame:
        if definition.source == "bcb":
            if not definition.provider_code:
                raise ValueError(f"Serie BCB sem provider_code definido: {definition.series_code}")

            return self.bcb_client.get_series(
                definition.provider_code,
                start=definition.start,
                end=definition.end,
            )

        if definition.source == "ipea":
            if not definition.provider_code:
                raise ValueError(f"Serie IPEA sem provider_code definido: {definition.series_code}")

            return self.ipea_client.get_series(
                definition.provider_code,
                start=definition.start,
                end=definition.end,
            )

        if definition.source == "sidra":
            if not definition.request_url:
                raise ValueError(f"Serie SIDRA sem request_url definida: {definition.series_code}")

            return self.sidra_client.get_series(
                definition.request_url,
                filters=definition.filters,
                start=definition.start,
                end=definition.end,
            )

        raise ValueError(f"Fonte macroeconomica nao suportada: {definition.source}")

    def _standardize_series(
        self,
        definition: MacroSeriesDefinition,
        series_frame: pd.DataFrame,
    ) -> pd.DataFrame:
        standardized = series_frame.reset_index().rename(columns={series_frame.columns[0]: "value"})
        standardized["date"] = pd.to_datetime(standardized["date"], errors="coerce")
        standardized["source"] = definition.source
        standardized["series_code"] = definition.series_code
        standardized["series_name"] = definition.series_name
        standardized["value"] = pd.to_numeric(standardized["value"], errors="coerce")
        standardized = standardized.dropna(subset=["date", "value"])

        return standardized[PIPELINE_COLUMNS].copy()

    @staticmethod
    def _combine_frames(frames: Sequence[pd.DataFrame]) -> pd.DataFrame:
        if not frames:
            return pd.DataFrame(columns=PIPELINE_COLUMNS)

        combined = pd.concat(frames, ignore_index=True)
        combined = combined.sort_values(["date", "source", "series_code"]).reset_index(drop=True)
        return combined[PIPELINE_COLUMNS].copy()

    @staticmethod
    def to_wide(frame: pd.DataFrame) -> pd.DataFrame:
        """Converte o formato longo consolidado para colunas por serie."""
        if frame.empty:
            empty = pd.DataFrame()
            empty.index.name = "date"
            return empty

        wide = (
            frame.pivot_table(
                index="date",
                columns="series_code",
                values="value",
                aggfunc="last",
            )
            .sort_index()
            .sort_index(axis=1)
        )
        wide.index.name = "date"
        return wide
