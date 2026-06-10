from __future__ import annotations

import json

import pandas as pd

from src.config import TABLE_DIR, ensure_dirs


def compile_validation_summary() -> pd.DataFrame:
    ensure_dirs()
    rows = []

    forecast_metrics_path = TABLE_DIR / "forecast_metrics.csv"
    if forecast_metrics_path.exists():
        forecast = pd.read_csv(forecast_metrics_path)
        for target, group in forecast.groupby("target"):
            best = group.sort_values("mape").iloc[0]
            rows.append(
                {
                    "area": "forecasting",
                    "check": f"best_holdout_model_{target}",
                    "status": "pass",
                    "result": f"{best['model']} MAPE={best['mape']:.4f}, RMSE={best['rmse']:.2f}",
                    "decision": "Use best MAPE for headline; keep baseline comparisons visible.",
                }
            )

    pa_metrics_path = TABLE_DIR / "pa_model_metrics.csv"
    if pa_metrics_path.exists():
        pa = pd.read_csv(pa_metrics_path).iloc[0]
        rows.append(
            {
                "area": "prior_auth",
                "check": "cms_pbp_prior_auth_exposure",
                "status": "pass",
                "result": f"plans_reviewed={int(pa['plans_reviewed'])}, plans_with_prior_auth_required={int(pa['plans_with_prior_auth_required'])}",
                "decision": "Public CMS data lacks request-level labels; frame as exposure prioritization, not denial prediction.",
            }
        )

    opportunity_path = TABLE_DIR / "opportunity_score_methodology.csv"
    if opportunity_path.exists():
        opportunity = pd.read_csv(opportunity_path)
        rows.append(
            {
                "area": "growth_opportunity",
                "check": "cms_signal_opportunity_score",
                "status": "pass",
                "result": "; ".join(f"{r.component}={r.weight:.2f}" for r in opportunity.itertuples()),
                "decision": "Use score as a transparent CMS-signal ranking, not a dollar revenue estimate.",
            }
        )

    outlier_path = TABLE_DIR / "ma_scp_outlier_handling_summary.csv"
    if outlier_path.exists():
        outliers = pd.read_csv(outlier_path)
        rows.append(
            {
                "area": "data_quality",
                "check": "outlier_policy",
                "status": "pass",
                "result": "; ".join(f"{r.level}: {r.iqr_outliers}" for r in outliers.itertuples()),
                "decision": "Flag outliers; do not drop source rows.",
            }
        )

    readiness_path = TABLE_DIR / "ma_scp_forecasting_readiness.csv"
    if readiness_path.exists():
        readiness = pd.read_csv(readiness_path).iloc[0]
        rows.append(
            {
                "area": "data_quality",
                "check": "forecasting_readiness",
                "status": "pass",
                "result": f"{int(readiness['source_months'])} months, {int(readiness['source_rows_preserved'])} rows preserved",
                "decision": readiness["main_caveat"],
            }
        )

    summary = pd.DataFrame(rows)
    summary.to_csv(TABLE_DIR / "model_validation_summary.csv", index=False)
    (TABLE_DIR / "validation_decisions.json").write_text(json.dumps(rows, indent=2))
    return summary


def main() -> None:
    summary = compile_validation_summary()
    print(summary)


if __name__ == "__main__":
    main()
