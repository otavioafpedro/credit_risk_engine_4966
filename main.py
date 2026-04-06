from __future__ import annotations

import os

import pandas as pd

from config import (
    DISCOUNT_RATE_ANNUAL,
    MONTHS_FORWARD,
    N_CLIENTS,
    RANDOM_STATE,
    SECTOR_TIME_SERIES_MONTHS,
)
from src.data_generation import SyntheticCreditDataGenerator
from src.ead_model import EADModel
from src.ecl_engine import calculate_ecl
from src.lgd_model import LGDModel
from src.pd_model import PDModel
from src.portfolio_policy import (
    build_sector_attractiveness_index,
    build_sector_policy_flags,
    indicative_sector_pricing,
)
from src.reporting import (
    plot_ecl_by_scenario,
    plot_pd_lgd_heatmap,
    plot_pd_vs_observed,
    plot_sector_correlation_heatmap,
    plot_sector_exposure,
    plot_sector_ranking,
    plot_stage_distribution,
    plot_sector_risk_bubble
)
from src.sector_risk import (
    build_sector_time_series,
    find_natural_hedges,
    sector_correlation_matrix,
    sector_exposure_summary,
    sector_hhi,
)
from src.staging import assign_stage
from src.stress_testing import SCENARIOS, apply_scenario, apply_macro_overlay
from src.validation import calibration_table, population_stability_index, score_pd_model


def main() -> None:
    os.makedirs("data/outputs/charts", exist_ok=True)

    generator = SyntheticCreditDataGenerator(
        n_clients=N_CLIENTS,
        random_state=RANDOM_STATE,
    )
    df = generator.generate()

    pd_model = PDModel(random_state=RANDOM_STATE)
    pd_result = pd_model.fit(df)
    df["pd_12m_model"] = pd_model.predict_pd_12m(df)

    lgd_model = LGDModel(random_state=RANDOM_STATE)
    lgd_mae = lgd_model.fit(df)
    df["lgd_model"] = lgd_model.predict_lgd(df)

    ead_model = EADModel(random_state=RANDOM_STATE)
    ead_mae = ead_model.fit(df)
    df["ead_model"] = ead_model.predict_ead(df)

    df["stage"] = assign_stage(df, df["pd_12m_model"].values)

    ecl_df = calculate_ecl(
        pd_12m=df["pd_12m_model"].values,
        lgd=df["lgd_model"].values,
        ead=df["ead_model"].values,
        stage=df["stage"],
        months_forward=MONTHS_FORWARD,
        annual_rate=DISCOUNT_RATE_ANNUAL,
    )

    result = pd.concat(
        [df, ecl_df[["ecl_12m", "ecl_lifetime", "final_ecl"]]],
        axis=1,
    )

    val_metrics = score_pd_model(result["default_12m"], result["pd_12m_model"])
    calib = calibration_table(result["default_12m"], result["pd_12m_model"])
    psi = population_stability_index(result["true_pd_12m"], result["pd_12m_model"])

    scenarios_summary: list[dict] = []
    for scenario_name in SCENARIOS:
        stressed = apply_scenario(df, scenario_name)

        base_pd = pd_model.predict_pd_12m(stressed)
        base_lgd = lgd_model.predict_lgd(stressed)
        base_ead = ead_model.predict_ead(stressed)

        stressed_pd, stressed_lgd = apply_macro_overlay(
            pd_values=base_pd,
            lgd_values=base_lgd,
            scenario_name=scenario_name,
        )

        stressed["pd_12m_model"] = stressed_pd
        stressed["lgd_model"] = stressed_lgd
        stressed["ead_model"] = base_ead
        stressed["stage"] = assign_stage(stressed, stressed["pd_12m_model"].values)

        stressed_ecl = calculate_ecl(
            pd_12m=stressed["pd_12m_model"].values,
            lgd=stressed["lgd_model"].values,
            ead=stressed["ead_model"].values,
            stage=stressed["stage"],
            months_forward=MONTHS_FORWARD,
            annual_rate=DISCOUNT_RATE_ANNUAL,
        )

        scenarios_summary.append(
            {
                "scenario": scenario_name,
                "total_ecl": float(stressed_ecl["final_ecl"].sum()),
                "avg_pd": float(stressed["pd_12m_model"].mean()),
                "avg_lgd": float(stressed["lgd_model"].mean()),
                "avg_ead": float(stressed["ead_model"].mean()),
                "stage2_plus_share": float((stressed["stage"] >= 2).mean()),
            }
        )

    scenarios_df = pd.DataFrame(scenarios_summary)

    sector_summary = sector_exposure_summary(result)
    portfolio_hhi = sector_hhi(sector_summary)

    sector_ts = build_sector_time_series(
        n_months=SECTOR_TIME_SERIES_MONTHS,
        random_state=RANDOM_STATE,
    )
    corr_matrix = sector_correlation_matrix(sector_ts)
    hedges = find_natural_hedges(corr_matrix, threshold=0.0)

    sector_policy = build_sector_policy_flags(sector_summary)
    sector_pricing = indicative_sector_pricing(sector_policy)

    sector_attractiveness = build_sector_attractiveness_index(
        exposure_df=sector_pricing,
        corr_matrix=corr_matrix,
        top_n_dominant=3,
        w_spread=0.30,
        w_pd=0.25,
        w_lgd=0.15,
        w_concentration=0.15,
        w_corr=0.15,
    )

    result.to_excel("data/outputs/portfolio_ecl_results.xlsx", index=False)
    calib.to_excel("data/outputs/pd_calibration_table.xlsx", index=False)
    scenarios_df.to_excel("data/outputs/scenario_summary.xlsx", index=False)
    sector_summary.to_excel("data/outputs/sector_summary.xlsx", index=False)
    sector_policy.to_excel("data/outputs/sector_policy.xlsx", index=False)
    sector_pricing.to_excel("data/outputs/sector_pricing.xlsx", index=False)
    corr_matrix.to_excel("data/outputs/sector_corr_matrix.xlsx")
    hedges.to_excel("data/outputs/natural_hedges.xlsx", index=False)
    sector_attractiveness.to_excel("data/outputs/sector_attractiveness.xlsx", index=False)

    plot_stage_distribution(result, "data/outputs/charts/stage_distribution.png")
    plot_ecl_by_scenario(scenarios_df, "data/outputs/charts/ecl_by_scenario.png")
    plot_pd_lgd_heatmap(result, "data/outputs/charts/pd_lgd_heatmap.png")
    plot_sector_correlation_heatmap(
        corr_matrix,
        "data/outputs/charts/sector_correlation_heatmap.png",
    )
    plot_sector_ranking(
        sector_attractiveness,
        "data/outputs/charts/sector_ranking.png",
    )
    plot_sector_exposure(
        sector_summary,
        "data/outputs/charts/sector_exposure.png",
    )
    plot_pd_vs_observed(
        calib,
        "data/outputs/charts/pd_calibration.png",
    )
    plot_sector_risk_bubble(
    sector_summary,
    "data/outputs/charts/sector_risk_bubble.png",
    )

    print("=== RESULTADOS PRINCIPAIS ===")
    print(f"PD AUC: {val_metrics['auc']:.4f}")
    print(f"PD Brier: {val_metrics['brier']:.4f}")
    print(f"PD model fit AUC (holdout): {pd_result.auc:.4f}")
    print(f"PD model fit Brier (holdout): {pd_result.brier:.4f}")
    print(f"LGD MAE: {lgd_mae:.4f}")
    print(f"EAD MAE: {ead_mae:.2f}")
    print(f"PSI true_pd vs model_pd: {psi:.4f}")
    print(f"ECL total (base): {result['final_ecl'].sum():,.2f}")
    print(f"HHI setorial da carteira: {portfolio_hhi:.4f}")

    print("\nResumo de cenários:")
    print(scenarios_df)

    print("\nSetores potencialmente úteis como hedge natural:")
    if hedges.empty:
        print("Nenhum par com correlação <= 0 encontrado nesta simulação.")
    else:
        print(hedges.head(10))

    print("\nTop setores por atratividade ajustada ao risco:")
    print(
        sector_attractiveness[
            [
                "sector",
                "sector_attractiveness_index",
                "sector_attractiveness_rank",
                "strategic_bucket",
                "avg_pd",
                "avg_lgd",
                "ead_share",
                "marginal_corr_to_book",
                "indicative_spread",
            ]
        ]
    )


if __name__ == "__main__":
    main()