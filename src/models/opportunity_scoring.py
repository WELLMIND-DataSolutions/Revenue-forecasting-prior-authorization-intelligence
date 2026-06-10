from __future__ import annotations

import zipfile

import pandas as pd

from src.config import RAW_DIR, TABLE_DIR, ensure_dirs


PENETRATION_DIR = RAW_DIR / "ma_penetration"


STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI",
    "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND",
    "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
    "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY", "Puerto Rico": "PR",
}


def _number(value: object) -> float:
    text = str(value).replace(",", "").replace("%", "").strip()
    if text in {"", "*", "nan", "None"}:
        return float("nan")
    return float(text)


def load_penetration() -> pd.DataFrame:
    zip_files = sorted(PENETRATION_DIR.glob("*.zip"))
    if not zip_files:
        raise FileNotFoundError(f"No MA penetration ZIP found under {PENETRATION_DIR}")
    zip_path = zip_files[-1]
    with zipfile.ZipFile(zip_path) as zf:
        csv_name = next(name for name in zf.namelist() if name.lower().endswith(".csv"))
        with zf.open(csv_name) as handle:
            df = pd.read_csv(handle, dtype=str)
    out = df.rename(
        columns={
            "State Name": "state_name",
            "County Name": "county",
            "FIPS": "fips",
            "Eligibles": "eligible_beneficiaries",
            "Enrolled": "ma_enrolled",
            "Penetration": "ma_penetration",
        }
    )
    out["state"] = out["state_name"].map(STATE_ABBR)
    out["eligible_beneficiaries"] = out["eligible_beneficiaries"].map(_number)
    out["ma_enrolled"] = out["ma_enrolled"].map(_number)
    out["ma_penetration"] = out["ma_penetration"].map(_number) / 100
    out["fips"] = out["fips"].astype(str).str.zfill(5)
    return out[["state", "state_name", "county", "fips", "eligible_beneficiaries", "ma_enrolled", "ma_penetration"]]


def percentile(series: pd.Series) -> pd.Series:
    return series.rank(pct=True).fillna(0)


def score_opportunities() -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_dirs()
    state_growth = pd.read_csv(TABLE_DIR / "ma_scp_state_growth.csv")
    county_growth = pd.read_csv(TABLE_DIR / "ma_scp_county_growth.csv")
    penetration = load_penetration()

    state_pen = (
        penetration.groupby("state", as_index=False)
        .agg(
            eligible_beneficiaries=("eligible_beneficiaries", "sum"),
            penetration_enrolled=("ma_enrolled", "sum"),
        )
    )
    state_pen["ma_penetration"] = state_pen["penetration_enrolled"] / state_pen["eligible_beneficiaries"]

    state = state_growth.merge(state_pen[["state", "eligible_beneficiaries", "ma_penetration"]], on="state", how="left")
    state["growth_rate_rank"] = percentile(state["growth_pct"])
    state["enrollment_scale_rank"] = percentile(state["last_enrollment"])
    state["penetration_rank"] = percentile(state["ma_penetration"])
    state["momentum_rank"] = percentile(state["avg_mom_growth_pct"])
    state["opportunity_score"] = (
        100
        * (
            0.40 * state["growth_rate_rank"]
            + 0.30 * state["enrollment_scale_rank"]
            + 0.20 * state["penetration_rank"]
            + 0.10 * state["momentum_rank"]
        )
    ).round(2)
    state["score_explanation"] = (
        "Weighted CMS ranking: 40% growth rate, 30% enrollment scale, 20% MA penetration, 10% monthly momentum"
    )
    state["recommendation"] = state.apply(
        lambda r: f"Prioritize {r['state']} for RCM outreach: score {r['opportunity_score']:.1f}, "
        f"latest enrollment {r['last_enrollment']:,.0f}, growth {r['growth_pct']:.2%}.",
        axis=1,
    )
    state = state.sort_values("opportunity_score", ascending=False)

    county = county_growth.merge(
        penetration[["state", "county", "fips", "eligible_beneficiaries", "ma_penetration"]],
        left_on=["state", "county"],
        right_on=["state", "county"],
        how="left",
    )
    county["growth_rate_rank"] = percentile(county["growth_pct"])
    county["enrollment_scale_rank"] = percentile(county["last_enrollment"])
    county["penetration_rank"] = percentile(county["ma_penetration"])
    county["momentum_rank"] = percentile(county["avg_mom_growth_pct"])
    county["opportunity_score"] = (
        100
        * (
            0.40 * county["growth_rate_rank"]
            + 0.30 * county["enrollment_scale_rank"]
            + 0.20 * county["penetration_rank"]
            + 0.10 * county["momentum_rank"]
        )
    ).round(2)
    county["score_explanation"] = state["score_explanation"].iloc[0]
    county["recommendation"] = county.apply(
        lambda r: f"Review {r['state']} {r['county']} for market outreach: score {r['opportunity_score']:.1f}, "
        f"latest enrollment {r['last_enrollment']:,.0f}, growth {r['growth_pct']:.2%}.",
        axis=1,
    )
    county = county.sort_values("opportunity_score", ascending=False)

    state.to_csv(TABLE_DIR / "dashboard_state_opportunities.csv", index=False)
    county.to_csv(TABLE_DIR / "dashboard_county_opportunities.csv", index=False)
    pd.DataFrame(
        [
            {"component": "growth_rate_rank", "weight": 0.40, "source": "CMS MA SCP first-to-last observed enrollment growth"},
            {"component": "enrollment_scale_rank", "weight": 0.30, "source": "CMS MA SCP latest observed enrollment"},
            {"component": "penetration_rank", "weight": 0.20, "source": "CMS MA state/county penetration file"},
            {"component": "momentum_rank", "weight": 0.10, "source": "CMS MA SCP average month-over-month growth"},
        ]
    ).to_csv(TABLE_DIR / "opportunity_score_methodology.csv", index=False)
    return state, county


def main() -> None:
    state, county = score_opportunities()
    print(state[["state", "opportunity_score", "last_enrollment", "growth_pct", "ma_penetration"]].head(10).to_string(index=False))
    print(county[["state", "county", "opportunity_score", "last_enrollment", "growth_pct", "ma_penetration"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
