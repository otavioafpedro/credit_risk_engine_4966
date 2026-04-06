from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


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