from __future__ import annotations

import pandas as pd

from src.config import PROCESSED_DIR, TABLE_DIR, ensure_dirs


STANDARD_LIMIT_HOURS = 7 * 24
EXPEDITED_LIMIT_HOURS = 72


def _bucket(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _driver(row: pd.Series) -> str:
    drivers: list[str] = []
    if row["auth_required"]:
        drivers.append("CMS PBP prior authorization requirement")
    if row["total_auth_category_count"] >= row["p75_total_auth_categories"]:
        drivers.append("High number of authorization service categories")
    if row["is_snp"] == "Yes":
        drivers.append("SNP plan operational complexity")
    drivers.append("CMS decision timing guardrails: 72 hours expedited, 7 days standard")
    return "; ".join(drivers)


def _recommendation(row: pd.Series) -> str:
    if row["risk_bucket"] == "high":
        return "Pre-check documentation and submit early against CMS timing clock"
    if row["risk_bucket"] == "medium":
        return "Monitor authorization clock and confirm required documents"
    return "Standard timing monitoring"


def run_delay_model() -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_dirs()
    pa_path = PROCESSED_DIR / "prior_auth_exposure.csv"
    if not pa_path.exists():
        pa_path = PROCESSED_DIR / "pa_predictions.csv"
    pa = pd.read_csv(pa_path)
    p75 = float(pa["total_auth_category_count"].quantile(0.75))
    max_categories = max(float(pa["total_auth_category_count"].max()), 1.0)

    exposure = pa[
        [
            "contract_id",
            "plan_id",
            "segment_id",
            "organization",
            "plan_name",
            "plan_type",
            "is_snp",
            "auth_required",
            "total_auth_category_count",
            "prior_auth_exposure_score",
        ]
    ].copy()
    exposure["p75_total_auth_categories"] = p75
    exposure["cms_standard_limit_hours"] = STANDARD_LIMIT_HOURS
    exposure["cms_expedited_limit_hours"] = EXPEDITED_LIMIT_HOURS
    exposure["timing_exposure_score"] = (exposure["total_auth_category_count"] / max_categories).where(exposure["auth_required"], 0.0).round(4)
    exposure["risk_bucket"] = exposure["timing_exposure_score"].map(_bucket)
    exposure["drivers"] = exposure.apply(_driver, axis=1)
    exposure["recommendation"] = exposure.apply(_recommendation, axis=1)
    exposure = exposure.sort_values(["timing_exposure_score", "total_auth_category_count"], ascending=False)

    summary = (
        exposure.groupby(["plan_type", "risk_bucket"], as_index=False)
        .agg(
            plans=("contract_id", "count"),
            avg_auth_categories=("total_auth_category_count", "mean"),
            avg_timing_exposure=("timing_exposure_score", "mean"),
        )
        .sort_values(["avg_timing_exposure", "plans"], ascending=False)
    )
    exposure.to_csv(PROCESSED_DIR / "delay_predictions.csv", index=False)
    exposure.to_csv(PROCESSED_DIR / "auth_timing_exposure.csv", index=False)
    summary.to_csv(TABLE_DIR / "delay_risk_summary.csv", index=False)
    summary.to_csv(TABLE_DIR / "dashboard_delay_summary.csv", index=False)
    return exposure, summary


def main() -> None:
    delays, summary = run_delay_model()
    print(summary.head(10).to_string(index=False))
    print(f"Wrote {len(delays):,} timing exposure rows.")


if __name__ == "__main__":
    main()
