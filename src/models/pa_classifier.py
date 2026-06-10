from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.config import RAW_DIR, PROCESSED_DIR, TABLE_DIR, ensure_dirs


BENEFIT_DIR = RAW_DIR / "benefits"


def _as_list(value: object) -> list:
    if isinstance(value, list):
        return value
    return []


def _plan_id(value: object) -> str:
    return str(value).zfill(3) if value is not None else ""


def _risk_bucket(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _drivers(row: pd.Series) -> str:
    reasons: list[str] = []
    if row["auth_required"]:
        reasons.append("CMS PBP indicates prior authorization required")
    if row["medicare_auth_category_count"] >= row["p75_medicare_auth_categories"]:
        reasons.append("High count of Medicare service categories requiring authorization")
    if row["non_medicare_auth_category_count"] > 0:
        reasons.append("Supplemental/non-Medicare categories also require authorization")
    if row["is_snp"] == "Yes":
        reasons.append("SNP plan: operational documentation complexity may be higher")
    return "; ".join(reasons) if reasons else "No in-network prior authorization categories listed in PBP file"


def _recommendation(row: pd.Series) -> str:
    if row["risk_bucket"] == "high":
        return "Prioritize documentation checklist before submission"
    if row["risk_bucket"] == "medium":
        return "Review medical necessity and plan authorization rules"
    return "Standard authorization workflow"


def extract_benefit_prior_auth() -> pd.DataFrame:
    rows: list[dict] = []
    for path in sorted(BENEFIT_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            payload = json.loads(path.read_text())

        for plan in payload.get("pbp", []):
            characteristics = plan.get("planCharacteristics") or {}
            pa_details = (
                ((plan.get("priorAuthorizationAndReferral") or {}).get("priorAuthorization") or {})
                .get("priorAuthorizationDetails")
                or {}
            )
            selections = pa_details.get("inNetworkAuthServiceCategorySelections") or {}
            medicare_categories = _as_list(selections.get("medicare")) if isinstance(selections, dict) else []
            non_medicare_categories = _as_list(selections.get("nonMedicare")) if isinstance(selections, dict) else []
            required_flag = str(pa_details.get("inNetworkAuthServiceCategoryRequired") or "").strip()
            auth_required = required_flag == "1" or bool(medicare_categories or non_medicare_categories)

            rows.append(
                {
                    "source_file": path.name,
                    "contract_year": payload.get("contractYear"),
                    "contract_id": plan.get("contractId"),
                    "plan_id": _plan_id(plan.get("planId")),
                    "segment_id": plan.get("segmentId"),
                    "organization": characteristics.get("organizationMarketingName"),
                    "contract_legal_name": characteristics.get("contractLegalName"),
                    "plan_name": characteristics.get("planName"),
                    "plan_type": characteristics.get("planTypeLabel"),
                    "is_snp": characteristics.get("isSnp"),
                    "snp_type": characteristics.get("snpType"),
                    "auth_required_flag_raw": required_flag,
                    "auth_required": auth_required,
                    "medicare_auth_category_count": len(medicare_categories),
                    "non_medicare_auth_category_count": len(non_medicare_categories),
                    "total_auth_category_count": len(medicare_categories) + len(non_medicare_categories),
                    "medicare_auth_categories": "|".join(medicare_categories),
                    "non_medicare_auth_categories": "|".join(non_medicare_categories),
                }
            )

    if not rows:
        raise FileNotFoundError(f"No benefit JSON files found under {BENEFIT_DIR}")
    return pd.DataFrame(rows)


def score_prior_auth_exposure(plans: pd.DataFrame) -> pd.DataFrame:
    out = plans.copy()
    p75 = float(out["medicare_auth_category_count"].quantile(0.75))
    max_categories = max(float(out["total_auth_category_count"].max()), 1.0)
    out["p75_medicare_auth_categories"] = p75
    out["auth_category_intensity"] = out["total_auth_category_count"] / max_categories
    out["prior_auth_exposure_score"] = out["auth_category_intensity"].where(out["auth_required"], 0.0).round(4)
    out["risk_bucket"] = out["prior_auth_exposure_score"].map(_risk_bucket)
    out["drivers"] = out.apply(_drivers, axis=1)
    out["recommendation"] = out.apply(_recommendation, axis=1)
    return out.sort_values(["prior_auth_exposure_score", "total_auth_category_count"], ascending=False)


def run_pa_model() -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_dirs()
    scored = score_prior_auth_exposure(extract_benefit_prior_auth())
    summary = (
        scored.groupby(["plan_type", "risk_bucket"], as_index=False)
        .agg(
            plans=("source_file", "count"),
            plans_with_auth=("auth_required", "sum"),
            avg_auth_categories=("total_auth_category_count", "mean"),
            avg_exposure_score=("prior_auth_exposure_score", "mean"),
        )
        .sort_values(["avg_exposure_score", "plans"], ascending=False)
    )
    metrics = pd.DataFrame(
        [
            {
                "engine": "cms_pbp_prior_auth_exposure",
                "source": "CMS 2026 PBP benefit JSON priorAuthorizationAndReferral fields",
                "plans_reviewed": len(scored),
                "plans_with_prior_auth_required": int(scored["auth_required"].sum()),
                "high_exposure_plans": int(scored["risk_bucket"].eq("high").sum()),
                "label_status": "No request-level approval/denial labels in public CMS files",
                "model_status": "Rule-based CMS feature extraction, not supervised denial prediction",
            }
        ]
    )

    scored.to_csv(PROCESSED_DIR / "pa_predictions.csv", index=False)
    scored.to_csv(PROCESSED_DIR / "prior_auth_exposure.csv", index=False)
    summary.to_csv(TABLE_DIR / "dashboard_pa_summary.csv", index=False)
    summary.to_csv(TABLE_DIR / "pa_risk_by_procedure_payer.csv", index=False)
    metrics.to_csv(TABLE_DIR / "pa_model_metrics.csv", index=False)
    return scored, metrics


def main() -> None:
    predictions, metrics = run_pa_model()
    print(metrics.to_string(index=False))
    print(predictions.head().to_string(index=False))


if __name__ == "__main__":
    main()
