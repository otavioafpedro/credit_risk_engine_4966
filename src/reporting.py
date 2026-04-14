from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd


matplotlib.use("Agg")
import matplotlib.pyplot as plt


OUTPUT_DPI = 180


def _prepare_output(path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _base_style(figsize: tuple[float, float] = (9, 5.2)) -> None:
    plt.figure(figsize=figsize)
    ax = plt.gca()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.20)
    ax.set_axisbelow(True)


def plot_stage_distribution(df: pd.DataFrame, path: str) -> None:
    counts = df["stage"].value_counts().sort_index()
    _base_style()
    counts.plot(kind="bar")
    plt.title("Distribuição por estágio")
    plt.xlabel("Estágio")
    plt.ylabel("Quantidade")
    plt.tight_layout()
    plt.savefig(_prepare_output(path), dpi=OUTPUT_DPI, bbox_inches="tight")
    plt.close()


def plot_ecl_by_scenario(scenario_df: pd.DataFrame, path: str) -> None:
    _base_style()
    scenario_df.set_index("scenario")["total_ecl"].plot(kind="bar")
    plt.title("ECL total por cenário")
    plt.xlabel("Cenário")
    plt.ylabel("ECL")
    plt.tight_layout()
    plt.savefig(_prepare_output(path), dpi=OUTPUT_DPI, bbox_inches="tight")
    plt.close()


def plot_pd_lgd_heatmap(df: pd.DataFrame, path: str, bins: int = 6) -> None:
    data = df[["pd_12m_model", "lgd_model", "ead_model"]].copy()
    data["pd_bucket"] = pd.qcut(data["pd_12m_model"], q=bins, duplicates="drop")
    data["lgd_bucket"] = pd.qcut(data["lgd_model"], q=bins, duplicates="drop")

    heatmap = data.pivot_table(
    index="lgd_bucket",
    columns="pd_bucket",
    values="ead_model",
    aggfunc="sum",
    fill_value=0.0,
    observed=False,
    )

    matrix = heatmap.values
    _base_style(figsize=(9.2, 6.0))
    plt.grid(False)
    plt.imshow(matrix, aspect="auto")
    plt.colorbar(label="EAD agregado")
    plt.title("Heatmap PD × LGD")
    plt.xlabel("Faixas de PD")
    plt.ylabel("Faixas de LGD")
    plt.xticks(
        ticks=np.arange(len(heatmap.columns)),
        labels=[str(c) for c in heatmap.columns],
        rotation=35,
        ha="right",
    )
    plt.yticks(
        ticks=np.arange(len(heatmap.index)),
        labels=[str(i) for i in heatmap.index],
    )

    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            val = matrix[i, j]
            if val > 0:
                plt.text(j, i, f"{val:,.0f}", ha="center", va="center", fontsize=8)

    plt.tight_layout()
    plt.savefig(_prepare_output(path), dpi=OUTPUT_DPI, bbox_inches="tight")
    plt.close()


def plot_sector_correlation_heatmap(corr_matrix: pd.DataFrame, path: str) -> None:
    matrix = corr_matrix.values
    labels = corr_matrix.columns.tolist()

    _base_style(figsize=(8.8, 6.5))
    plt.grid(False)
    plt.imshow(matrix, aspect="auto", vmin=-1, vmax=1)
    plt.colorbar(label="Correlação")
    plt.title("Correlação entre setores")
    plt.xticks(
        ticks=np.arange(len(labels)),
        labels=labels,
        rotation=35,
        ha="right",
    )
    plt.yticks(ticks=np.arange(len(labels)), labels=labels)

    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            plt.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center", fontsize=8)

    plt.tight_layout()
    plt.savefig(_prepare_output(path), dpi=OUTPUT_DPI, bbox_inches="tight")
    plt.close()


def plot_sector_ranking(
    sector_attractiveness: pd.DataFrame,
    path: str,
    top_n: int | None = None,
) -> None:
    df_plot = sector_attractiveness.copy()
    if top_n is not None:
        df_plot = df_plot.head(top_n)

    df_plot = df_plot.sort_values("sector_attractiveness_index", ascending=True)

    _base_style(figsize=(9, 5.8))
    plt.barh(df_plot["sector"], df_plot["sector_attractiveness_index"])
    plt.title("Ranking setorial por atratividade ajustada ao risco")
    plt.xlabel("Índice de atratividade")
    plt.ylabel("Setor")

    for i, value in enumerate(df_plot["sector_attractiveness_index"]):
        plt.text(value, i, f" {value:.3f}", va="center", fontsize=9)

    plt.tight_layout()
    plt.savefig(_prepare_output(path), dpi=OUTPUT_DPI, bbox_inches="tight")
    plt.close()


def plot_sector_exposure(sector_summary: pd.DataFrame, path: str) -> None:
    df_plot = sector_summary.sort_values("total_ead", ascending=False)

    _base_style(figsize=(9, 5.6))
    plt.bar(df_plot["sector"], df_plot["total_ead"])
    plt.title("Exposição total por setor")
    plt.xlabel("Setor")
    plt.ylabel("EAD total")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(_prepare_output(path), dpi=OUTPUT_DPI, bbox_inches="tight")
    plt.close()


def plot_pd_vs_observed(calibration_df: pd.DataFrame, path: str) -> None:
    _base_style(figsize=(6.8, 5.6))
    plt.grid(alpha=0.20)
    plt.scatter(calibration_df["avg_pd"], calibration_df["obs_rate"])

    upper = max(
        calibration_df["avg_pd"].max(),
        calibration_df["obs_rate"].max(),
    ) * 1.05

    plt.plot([0, upper], [0, upper])

    plt.title("Calibração: PD prevista vs default observado")
    plt.xlabel("PD média prevista")
    plt.ylabel("Taxa observada")
    plt.tight_layout()
    plt.savefig(_prepare_output(path), dpi=OUTPUT_DPI, bbox_inches="tight")
    plt.close()

def plot_sector_risk_bubble(sector_summary: pd.DataFrame, path: str) -> None:
    plt.figure(figsize=(9, 6))

    x = sector_summary["ead_share"]
    y = sector_summary["risk_cost"]
    sizes = sector_summary["total_ecl"] / sector_summary["total_ecl"].max() * 2000

    plt.scatter(x, y, s=sizes, alpha=0.6)

    for _, row in sector_summary.iterrows():
        plt.text(
            row["ead_share"],
            row["risk_cost"],
            row["sector"],
            fontsize=9,
            ha="center",
        )

    plt.xlabel("Participação no EAD (Concentração)")
    plt.ylabel("Custo de risco (ECL / EAD)")
    plt.title("Risco vs Concentração por setor")

    plt.grid(alpha=0.2)
    plt.tight_layout()
    plt.savefig(_prepare_output(path), dpi=OUTPUT_DPI, bbox_inches="tight")
    plt.close()


def plot_macro_credit_delinquency(reference_frame: pd.DataFrame, path: str) -> None:
    df_plot = reference_frame[
        ["delinquency_total", "delinquency_pf_total", "delinquency_pj_total"]
    ].dropna(how="all")
    if df_plot.empty:
        return

    _base_style(figsize=(9.4, 5.5))
    plt.plot(df_plot.index, df_plot["delinquency_total"] * 100.0, label="Total", linewidth=2.0)
    if "delinquency_pf_total" in df_plot.columns:
        plt.plot(df_plot.index, df_plot["delinquency_pf_total"] * 100.0, label="PF", alpha=0.90)
    if "delinquency_pj_total" in df_plot.columns:
        plt.plot(df_plot.index, df_plot["delinquency_pj_total"] * 100.0, label="PJ", alpha=0.90)

    plt.title("Inadimplencia agregada ao longo do tempo")
    plt.xlabel("Data")
    plt.ylabel("Percentual (%)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(_prepare_output(path), dpi=OUTPUT_DPI, bbox_inches="tight")
    plt.close()


def plot_macro_credit_spread_vs_selic(reference_frame: pd.DataFrame, path: str) -> None:
    df_plot = reference_frame[["spread_total", "selic_monthly_rate"]].dropna()
    if df_plot.empty:
        return

    _base_style(figsize=(9.4, 5.5))
    plt.plot(df_plot.index, df_plot["spread_total"] * 100.0, label="Spread total", linewidth=2.0)
    plt.plot(df_plot.index, df_plot["selic_monthly_rate"] * 100.0, label="Selic mensal", linewidth=2.0)
    plt.title("Spread agregado vs Selic")
    plt.xlabel("Data")
    plt.ylabel("Percentual (%)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(_prepare_output(path), dpi=OUTPUT_DPI, bbox_inches="tight")
    plt.close()


def plot_macro_credit_vs_activity(reference_frame: pd.DataFrame, path: str) -> None:
    df_plot = reference_frame[["credit_stock_total", "activity_level"]].dropna()
    if df_plot.empty:
        return

    normalized_credit = _normalize_to_base_100(df_plot["credit_stock_total"])
    normalized_activity = _normalize_to_base_100(df_plot["activity_level"])
    common_index = normalized_credit.index.intersection(normalized_activity.index)
    if common_index.empty:
        return

    _base_style(figsize=(9.4, 5.5))
    plt.plot(common_index, normalized_credit.loc[common_index], label="Credito total (base 100)", linewidth=2.0)
    plt.plot(common_index, normalized_activity.loc[common_index], label="Atividade (base 100)", linewidth=2.0)
    plt.title("Credito total vs atividade")
    plt.xlabel("Data")
    plt.ylabel("Indice normalizado")
    plt.legend()
    plt.tight_layout()
    plt.savefig(_prepare_output(path), dpi=OUTPUT_DPI, bbox_inches="tight")
    plt.close()


def plot_macro_credit_correlation_heatmap(corr_matrix: pd.DataFrame, path: str) -> None:
    if corr_matrix.empty:
        return

    matrix = corr_matrix.values
    labels = corr_matrix.columns.tolist()

    _base_style(figsize=(8.8, 6.5))
    plt.grid(False)
    plt.imshow(matrix, aspect="auto", vmin=-1, vmax=1)
    plt.colorbar(label="Correlacao")
    plt.title("Correlacao entre macro e credito agregado")
    plt.xticks(
        ticks=np.arange(len(labels)),
        labels=labels,
        rotation=35,
        ha="right",
    )
    plt.yticks(ticks=np.arange(len(labels)), labels=labels)

    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            plt.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center", fontsize=8)

    plt.tight_layout()
    plt.savefig(_prepare_output(path), dpi=OUTPUT_DPI, bbox_inches="tight")
    plt.close()


def _normalize_to_base_100(series: pd.Series) -> pd.Series:
    clean_series = series.dropna()
    if clean_series.empty:
        return clean_series

    base_value = clean_series.iloc[0]
    if base_value == 0:
        return clean_series * np.nan

    return clean_series / base_value * 100.0
