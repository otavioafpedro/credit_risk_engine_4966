from __future__ import annotations

from pathlib import Path

import pandas as pd

from config import MACRO_MAX_FFILL_MONTHS, MACRO_WIDE_PATH
from src.macro_credit_analytics import run_macro_credit_analysis
from src.reporting import (
    plot_macro_credit_correlation_heatmap,
    plot_macro_credit_delinquency,
    plot_macro_credit_spread_vs_selic,
    plot_macro_credit_vs_activity,
)


REFERENCE_SUMMARY_OUTPUT = Path("data/outputs/macro_credit_reference_summary.xlsx")
VALIDATION_OUTPUT = Path("data/outputs/macro_credit_validation.xlsx")
CHART_OUTPUTS = {
    "delinquency": Path("data/outputs/charts/macro_credit_delinquency.png"),
    "spread_vs_selic": Path("data/outputs/charts/macro_credit_spread_vs_selic.png"),
    "credit_vs_activity": Path("data/outputs/charts/macro_credit_credit_vs_activity.png"),
    "correlation_heatmap": Path("data/outputs/charts/macro_credit_correlation_heatmap.png"),
}


def main() -> None:
    analysis_result = run_macro_credit_analysis(
        MACRO_WIDE_PATH,
        max_ffill_months=MACRO_MAX_FFILL_MONTHS,
    )

    _write_reference_summary_workbook(analysis_result)
    _write_validation_workbook(analysis_result)
    _write_charts(analysis_result)

    print("=== MACRO CREDIT ANALYTICS ===")
    print(f"Linhas na base de referencia: {len(analysis_result.reference_frame)}")
    print(
        "Janela analisada: "
        f"{analysis_result.reference_frame.index.min().date()} "
        f"ate {analysis_result.reference_frame.index.max().date()}"
    )
    print(f"Workbook de resumo: {REFERENCE_SUMMARY_OUTPUT}")
    print(f"Workbook de validacao: {VALIDATION_OUTPUT}")

    print("\nSeries usadas:")
    for metric_name, series_code in analysis_result.selected_series.items():
        print(f"- {metric_name} <- {series_code}")

    if not analysis_result.reference_summary.empty:
        print("\nUltimos niveis de referencia:")
        latest_summary = analysis_result.reference_summary[["metric", "latest_date", "latest_value", "source_series"]]
        print(latest_summary.to_string(index=False))


def _write_reference_summary_workbook(analysis_result) -> None:
    REFERENCE_SUMMARY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    selected_series_df = pd.DataFrame(
        [
            {"metric": metric_name, "series_code": series_code}
            for metric_name, series_code in analysis_result.selected_series.items()
        ]
    ).sort_values("metric")

    with pd.ExcelWriter(REFERENCE_SUMMARY_OUTPUT) as writer:
        analysis_result.reference_summary.to_excel(writer, sheet_name="reference_summary", index=False)
        analysis_result.relationship_summary.to_excel(writer, sheet_name="relationship_summary", index=False)
        analysis_result.scenario_calibration.to_excel(writer, sheet_name="scenario_calibration", index=False)
        analysis_result.observed_scenario_overlays.to_excel(
            writer,
            sheet_name="scenario_overlays",
            index=False,
        )
        selected_series_df.to_excel(writer, sheet_name="selected_series", index=False)


def _write_validation_workbook(analysis_result) -> None:
    VALIDATION_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(VALIDATION_OUTPUT) as writer:
        analysis_result.reference_frame.reset_index().to_excel(writer, sheet_name="reference_frame", index=False)
        for sheet_name, frame in analysis_result.validation_tables.items():
            if sheet_name == "reference_frame":
                continue
            frame.reset_index().to_excel(writer, sheet_name=sheet_name[:31], index=False)
        analysis_result.correlation_matrix.to_excel(writer, sheet_name="correlation_matrix")


def _write_charts(analysis_result) -> None:
    plot_macro_credit_delinquency(analysis_result.reference_frame, str(CHART_OUTPUTS["delinquency"]))
    plot_macro_credit_spread_vs_selic(
        analysis_result.reference_frame,
        str(CHART_OUTPUTS["spread_vs_selic"]),
    )
    plot_macro_credit_vs_activity(
        analysis_result.reference_frame,
        str(CHART_OUTPUTS["credit_vs_activity"]),
    )
    plot_macro_credit_correlation_heatmap(
        analysis_result.correlation_matrix,
        str(CHART_OUTPUTS["correlation_heatmap"]),
    )


if __name__ == "__main__":
    main()
