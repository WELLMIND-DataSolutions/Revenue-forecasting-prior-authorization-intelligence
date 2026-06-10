from __future__ import annotations

import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.config import PROCESSED_DIR, TABLE_DIR


st.set_page_config(page_title="RCM Intelligence MVP", layout="wide")

STATE_NAME = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota",
    "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "PR": "Puerto Rico",
}


@st.cache_data
def load_data() -> dict[str, pd.DataFrame | dict]:
    data: dict[str, pd.DataFrame | dict] = {
        "monthly": pd.read_parquet(PROCESSED_DIR / "ma_scp_monthly_national.parquet"),
        "forecast": pd.read_csv(PROCESSED_DIR / "forecast_results.csv", parse_dates=["ds"]),
        "forecast_metrics": pd.read_csv(TABLE_DIR / "forecast_metrics.csv"),
        "state_growth": pd.read_csv(TABLE_DIR / "dashboard_state_opportunities.csv"),
        "county_opportunities": pd.read_csv(TABLE_DIR / "dashboard_county_opportunities.csv"),
        "opportunity_method": pd.read_csv(TABLE_DIR / "opportunity_score_methodology.csv"),
        "state_monthly": pd.read_parquet(PROCESSED_DIR / "ma_scp_state_monthly.parquet"),
        "plan_monthly": pd.read_parquet(PROCESSED_DIR / "ma_scp_plan_monthly.parquet"),
        "pa": pd.read_csv(PROCESSED_DIR / "pa_predictions.csv"),
        "pa_metrics": pd.read_csv(TABLE_DIR / "pa_model_metrics.csv"),
        "pa_summary": pd.read_csv(TABLE_DIR / "dashboard_pa_summary.csv"),
        "delay": pd.read_csv(PROCESSED_DIR / "delay_predictions.csv"),
        "delay_summary": pd.read_csv(TABLE_DIR / "dashboard_delay_summary.csv"),
        "validation": pd.read_csv(TABLE_DIR / "model_validation_summary.csv"),
        "cpsc_state": pd.read_csv(TABLE_DIR / "cpsc_latest_state_summary.csv"),
        "cpsc_plan_growth": pd.read_csv(TABLE_DIR / "cpsc_plan_growth.csv"),
    }
    decision_path = TABLE_DIR / "forecast_decision.json"
    data["forecast_decision"] = json.loads(decision_path.read_text()) if decision_path.exists() else {}
    return data


def pct(value: float) -> str:
    return f"{value:.2%}"


def whole(value: float) -> str:
    return f"{value:,.0f}"


def money(value: float) -> str:
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.1f}M"
    return f"${value:,.0f}"


def section_header(title: str, subtitle: str) -> None:
    st.subheader(title)
    st.caption(subtitle)


def metric_card(label: str, value: str, help_text: str | None = None) -> None:
    st.metric(label, value, help=help_text)


def csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8")


def target_series(monthly_frame: pd.DataFrame, target: str) -> pd.Series:
    return monthly_frame[target]


def baseline_future(monthly_frame: pd.DataFrame, target: str, model: str, periods: int = 3) -> pd.DataFrame:
    y = target_series(monthly_frame.sort_values("report_month"), target)
    if model == "naive_last_value":
        predicted = [y.iloc[-1]] * periods
    elif model == "moving_average_3m":
        predicted = [y.tail(3).mean()] * periods
    elif model == "linear_drift":
        drift = (y.iloc[-1] - y.iloc[0]) / max(len(y) - 1, 1)
        predicted = [y.iloc[-1] + drift * step for step in range(1, periods + 1)]
    else:
        return pd.DataFrame()

    future_dates = pd.date_range(monthly_frame["report_month"].max() + pd.offsets.MonthBegin(1), periods=periods, freq="MS")
    return pd.DataFrame(
        {
            "ds": future_dates,
            "actual": pd.NA,
            "yhat": predicted,
            "yhat_lower": predicted,
            "yhat_upper": predicted,
            "model": model,
            "target": target,
            "period_type": "future",
        }
    )


def future_forecast(forecast_frame: pd.DataFrame, monthly_frame: pd.DataFrame, target: str, model: str) -> pd.DataFrame:
    existing = forecast_frame[
        forecast_frame["target"].eq(target)
        & forecast_frame["model"].eq(model)
        & forecast_frame["period_type"].eq("future")
    ].sort_values("ds")
    if not existing.empty:
        return existing
    return baseline_future(monthly_frame, target, model).sort_values("ds")


data = load_data()
monthly = data["monthly"].copy()
forecast = data["forecast"].copy()
metrics = data["forecast_metrics"].copy()
state_growth = data["state_growth"].copy()
county_opportunities = data["county_opportunities"].copy()
opportunity_method = data["opportunity_method"].copy()
state_monthly = data["state_monthly"].copy()
plan_monthly = data["plan_monthly"].copy()
pa = data["pa"].copy()
pa_metrics = data["pa_metrics"].copy()
pa_summary = data["pa_summary"].copy()
delay = data["delay"].copy()
delay_summary = data["delay_summary"].copy()
validation = data["validation"].copy()
cpsc_state = data["cpsc_state"].copy()
cpsc_plan_growth = data["cpsc_plan_growth"].copy()

monthly["report_month"] = pd.to_datetime(monthly["report_month"])
state_monthly["report_month"] = pd.to_datetime(state_monthly["report_month"])
plan_monthly["report_month"] = pd.to_datetime(plan_monthly["report_month"])
state_growth["state_name"] = state_growth["state"].map(STATE_NAME).fillna(state_growth["state"])

best_models = metrics.sort_values(["target", "mape"]).groupby("target", as_index=False).first()
best_enrollment = best_models[best_models["target"].eq("observed_enrollment")].iloc[0]
best_model = best_enrollment["model"]

latest_month = monthly["report_month"].max()
latest_label = latest_month.strftime("%b %Y")
latest_enrollment = monthly.loc[monthly["report_month"].eq(latest_month), "observed_enrollment"].iloc[0]
first_enrollment = monthly["observed_enrollment"].iloc[0]
national_growth = latest_enrollment - first_enrollment
national_growth_pct = latest_enrollment / first_enrollment - 1

headline_forecast = future_forecast(forecast, monthly, "observed_enrollment", best_model)
next_month = headline_forecast.iloc[0]
final_future = headline_forecast.iloc[-1]
next_month_delta = next_month["yhat"] - latest_enrollment
ninety_day_delta = final_future["yhat"] - latest_enrollment

high_pa = pa[pa["risk_bucket"].eq("high")]
delay_high = delay[delay["risk_bucket"].eq("high")]

with st.sidebar:
    st.title("MVP Control Panel")
    st.caption("Enrollment opportunity forecasting, prior authorization exposure, timing exposure, and growth opportunity from public CMS data.")
    st.metric("CMS data window", f"{monthly['report_month'].min():%b %Y} - {latest_label}")
    st.divider()
    st.markdown("**Dashboard filters**")
    state_top_n = st.slider("Growth markets shown", min_value=10, max_value=50, value=25, step=5)
    pa_bucket_filter = st.multiselect(
        "PA risk buckets",
        options=["high", "medium", "low"],
        default=["high", "medium", "low"],
    )
    payer_filter = st.multiselect(
        "Plan types",
        options=sorted(pa["plan_type"].dropna().unique().tolist()),
        default=sorted(pa["plan_type"].dropna().unique().tolist()),
    )
    delay_bucket_filter = st.multiselect(
        "Delay risk buckets",
        options=["high", "medium", "low"],
        default=["high", "medium", "low"],
    )
    st.divider()
    st.markdown("**Public-data guardrail**")
    st.caption("No synthetic denial labels or PMPM revenue assumptions are used. PA and timing views are public CMS exposure scores, not denial predictions.")

filtered_state_growth = state_growth.head(state_top_n)
filtered_county = county_opportunities.head(state_top_n)
filtered_pa = pa[pa["risk_bucket"].isin(pa_bucket_filter) & pa["plan_type"].isin(payer_filter)].copy()
filtered_delay = delay[delay["risk_bucket"].isin(delay_bucket_filter)].copy()

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 2rem; max-width: 1500px;}
    h1 {font-size: 2.2rem; font-weight: 800; margin-bottom: 0.15rem;}
    h2, h3 {letter-spacing: 0;}
    div[data-testid="stMetric"] {background: #111827; border: 1px solid #243041; padding: 14px 16px; border-radius: 8px;}
    div[data-testid="stMetricLabel"] {font-size: 0.82rem;}
    .deliverable-note {border-left: 4px solid #38bdf8; padding: 10px 14px; background: rgba(56,189,248,0.08); border-radius: 4px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("RCM Opportunity Forecasting & Prior Authorization Intelligence")
st.caption("Executive MVP dashboard built from public CMS Medicare Advantage enrollment, penetration, plan, and prior-authorization benefit fields.")

overview, forecast_tab, growth_tab, pa_tab, delay_tab, plan_tab, validation_tab = st.tabs(
    [
        "Executive View",
        "90-Day Forecast",
        "Growth Opportunity",
        "PA Risk Prioritization",
        "Auth Timing Exposure",
        "Plan Intelligence",
        "Validation",
    ]
)

with overview:
    section_header(
        "Executive Decision Summary",
        "What an RCM sales or operations lead should take away first.",
    )
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Latest observed MA enrollment", whole(latest_enrollment), f"Latest CMS month: {latest_label}")
    with c2:
        metric_card("90-day projected enrollment lift", whole(ninety_day_delta), f"Model: {best_model}")
    with c3:
        metric_card("High PA exposure plans", whole(len(high_pa)), "Plans with many CMS PBP authorization categories")
    with c4:
        metric_card("High timing exposure plans", whole(len(delay_high)), "Plans with high authorization-category exposure against CMS timing guardrails")

    st.markdown(
        f"""
        <div class="deliverable-note">
        <b>Client hook:</b> next 90 days show an estimated <b>{whole(ninety_day_delta)}</b> additional observed MA enrollment
        on the public CMS trend line. CMS PBP benefit fields identify <b>{len(high_pa)}</b> high prior-authorization exposure plans and
        <b>{len(delay_high)}</b> high timing-exposure plans for operational review.
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.25, 1])
    with left:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=monthly["report_month"], y=monthly["observed_enrollment"], mode="lines+markers", name="CMS actual trend"))
        fig.add_trace(go.Scatter(x=headline_forecast["ds"], y=headline_forecast["yhat"], mode="lines+markers", name="90-day projection"))
        fig.update_layout(title="Actual CMS Enrollment Trend + 90-Day Projection", xaxis_title="", yaxis_title="Observed enrollment", height=390)
        st.plotly_chart(fig, width="stretch")
    with right:
        top_states = filtered_state_growth.head(7)[["state", "state_name", "opportunity_score", "absolute_growth", "growth_pct", "last_enrollment"]]
        st.markdown("**Top opportunity geographies**")
        st.dataframe(
            top_states.rename(
                columns={
                    "state": "State",
                    "state_name": "Market",
                    "absolute_growth": "Enrollment lift",
                    "growth_pct": "Growth %",
                    "opportunity_score": "Opportunity score",
                    "last_enrollment": "Latest enrollment",
                }
            ),
            width="stretch",
            hide_index=True,
        )

    st.markdown("**Deliverable coverage**")
    d1, d2, d3 = st.columns(3)
    d1.success("Forecast dashboard: CMS trend + 90-day projection")
    d2.success("PA intelligence: CMS PBP exposure queue + recommendations")
    d3.success("Growth opportunity: CMS growth + penetration ranking")
    st.download_button(
        "Download executive forecast extract",
        data=csv_bytes(headline_forecast),
        file_name="executive_90_day_forecast.csv",
        mime="text/csv",
    )

with forecast_tab:
    section_header(
        "Enrollment Opportunity Forecast",
        "Forecast vs actuals, model benchmark, and transparent public-data limitation statement.",
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Best model", best_model)
    c2.metric("Holdout MAPE", pct(best_enrollment["mape"]))
    c3.metric("Next-month enrollment lift", whole(next_month_delta))
    target_label = "Observed enrollment opportunity"
    target = "observed_enrollment"
    selected_best = best_models[best_models["target"].eq(target)].iloc[0]["model"]
    selected = forecast[forecast["target"].eq(target) & forecast["model"].eq(selected_best)].sort_values("ds")
    actual = monthly[["report_month", "observed_enrollment"]].rename(columns={"report_month": "ds", "observed_enrollment": "actual"})

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=actual["ds"], y=actual["actual"], mode="lines+markers", name="CMS actual"))
    future = future_forecast(forecast, monthly, target, selected_best)
    holdout = selected[selected["period_type"].eq("holdout")]
    fig.add_trace(go.Scatter(x=holdout["ds"], y=holdout["yhat"], mode="lines+markers", name="Holdout forecast"))
    fig.add_trace(go.Scatter(x=future["ds"], y=future["yhat"], mode="lines+markers", name="90-day forecast"))
    fig.update_layout(title=f"{target_label}: actuals, holdout, and 90-day forecast", xaxis_title="", yaxis_title=target_label, height=460)
    st.plotly_chart(fig, width="stretch")

    left, right = st.columns([1, 1])
    with left:
        st.markdown("**Model benchmark**")
        benchmark = metrics[metrics["target"].eq(target)].sort_values("mape").copy()
        benchmark["mape_pct"] = benchmark["mape"].map(lambda x: f"{x:.3%}")
        st.dataframe(benchmark[["model", "mae", "rmse", "mape_pct", "holdout_months"]], width="stretch", hide_index=True)
    with right:
        st.markdown("**Forecast decision**")
        st.write(
            "The dashboard headlines the lowest holdout-MAPE model. Prophet remains in the benchmark, but the short 29-month series favors the simpler linear drift model."
        )
        st.write("No PMPM revenue assumption is used. The forecast is an enrollment opportunity signal from public CMS data.")

with growth_tab:
    section_header(
        "Growth Opportunity Ranking",
        "Markets ranked using CMS growth, enrollment scale, MA penetration, and momentum.",
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("National growth since Jan 2024", whole(national_growth), pct(national_growth_pct))
    c2.metric("Top state score", state_growth.iloc[0]["state"], f"{state_growth.iloc[0]['opportunity_score']:.1f}")
    c3.metric("Top county score", f"{county_opportunities.iloc[0]['state']} {county_opportunities.iloc[0]['county']}", f"{county_opportunities.iloc[0]['opportunity_score']:.1f}")

    map_data = filtered_state_growth[filtered_state_growth["state"].isin(STATE_NAME)].copy()
    fig = px.choropleth(
        map_data,
        locations="state",
        locationmode="USA-states",
        color="opportunity_score",
        scope="usa",
        hover_name="state_name",
        hover_data={"growth_pct": ":.2%", "last_enrollment": ":,.0f", "ma_penetration": ":.2%", "state": False},
        color_continuous_scale="Blues",
        title="Regional opportunity heatmap: CMS-based opportunity score",
    )
    fig.update_layout(height=520)
    st.plotly_chart(fig, width="stretch")

    left, right = st.columns([1, 1])
    with left:
        fig = px.scatter(
            filtered_state_growth,
            x="last_enrollment",
            y="growth_pct",
            size=filtered_state_growth["opportunity_score"].clip(lower=1),
            color="ma_penetration",
            hover_name="state_name",
            title="Market scale vs growth rate, colored by MA penetration",
        )
        st.plotly_chart(fig, width="stretch")
    with right:
        fig = px.bar(filtered_state_growth.head(15), x="state", y="opportunity_score", title="Top states by opportunity score")
        st.plotly_chart(fig, width="stretch")

    left, right = st.columns([1, 1])
    with left:
        st.markdown("**Top 20 state markets**")
        st.dataframe(
            filtered_state_growth[["state", "state_name", "opportunity_score", "last_enrollment", "growth_pct", "ma_penetration", "recommendation"]].head(20),
            width="stretch",
            hide_index=True,
        )
    with right:
        st.markdown("**Top 20 county markets**")
        st.dataframe(
            filtered_county[["state", "county", "opportunity_score", "last_enrollment", "growth_pct", "ma_penetration", "recommendation"]].head(20),
            width="stretch",
            hide_index=True,
        )
    with st.expander("Opportunity score methodology"):
        st.dataframe(opportunity_method, width="stretch", hide_index=True)
        st.write("These are ranking weights, not revenue assumptions. Every score component is derived from public CMS enrollment or penetration data.")
        st.download_button(
            "Download growth opportunity report",
            data=csv_bytes(filtered_state_growth),
            file_name="growth_opportunity_report.csv",
            mime="text/csv",
        )

with pa_tab:
    section_header(
        "Prior Authorization Risk Prioritization Engine",
        "CMS PBP benefit-field exposure queue. This is not a supervised denial predictor because public CMS files do not contain request-level outcomes.",
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Plans reviewed", whole(pa_metrics.iloc[0]["plans_reviewed"]))
    c2.metric("Plans with PA required", whole(pa_metrics.iloc[0]["plans_with_prior_auth_required"]))
    c3.metric("High exposure plans", whole(len(high_pa)))
    c4.metric("Max exposure score", f"{pa['prior_auth_exposure_score'].max():.3f}")

    left, right = st.columns([1.1, 1])
    with left:
        fig = px.histogram(
            filtered_pa,
            x="prior_auth_exposure_score",
            color="risk_bucket",
            title="Prior authorization exposure distribution",
            color_discrete_map={"low": "#22c55e", "medium": "#f59e0b", "high": "#ef4444"},
        )
        st.plotly_chart(fig, width="stretch")
    with right:
        risk_by_proc = (
            filtered_pa.groupby(["plan_type", "risk_bucket"], as_index=False)
            .agg(avg_exposure=("prior_auth_exposure_score", "mean"), plans=("prior_auth_exposure_score", "size"))
            .sort_values("avg_exposure", ascending=False)
        )
        fig = px.bar(risk_by_proc.head(15), x="plan_type", y="avg_exposure", color="risk_bucket", title="PA exposure by plan type")
        st.plotly_chart(fig, width="stretch")

    st.markdown("**Explainable PA prioritization queue**")
    queue = filtered_pa.sort_values("prior_auth_exposure_score", ascending=False)[
        [
            "contract_id",
            "plan_id",
            "organization",
            "plan_name",
            "plan_type",
            "medicare_auth_category_count",
            "non_medicare_auth_category_count",
            "prior_auth_exposure_score",
            "risk_bucket",
            "drivers",
            "recommendation",
        ]
    ].head(25)
    st.dataframe(queue, width="stretch", hide_index=True)
    st.download_button(
        "Download PA strengthening queue",
        data=csv_bytes(queue),
        file_name="prior_auth_strengthening_queue.csv",
        mime="text/csv",
    )

with delay_tab:
    section_header(
        "Auth Timing Exposure",
        "Plan-level authorization workload exposure against CMS timing guardrails. This is not an observed delay predictor.",
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("High timing exposure plans", whole(len(delay_high)))
    c2.metric("Standard threshold", "7 days")
    c3.metric("Expedited threshold", "72 hours")

    fig = px.bar(
        filtered_delay.sort_values("timing_exposure_score", ascending=False).head(30),
        x="contract_id",
        y="timing_exposure_score",
        color="plan_type",
        title="Highest plan-level authorization timing exposure",
    )
    st.plotly_chart(fig, width="stretch")

    st.markdown("**High-exposure plans to review before submission workflows**")
    st.dataframe(
        filtered_delay.sort_values("timing_exposure_score", ascending=False)[
            ["contract_id", "plan_id", "organization", "plan_name", "plan_type", "total_auth_category_count", "cms_standard_limit_hours", "cms_expedited_limit_hours", "timing_exposure_score", "risk_bucket", "drivers", "recommendation"]
        ].head(25),
        width="stretch",
        hide_index=True,
    )
    st.download_button(
        "Download timing-exposure queue",
        data=csv_bytes(filtered_delay.sort_values("timing_exposure_score", ascending=False)),
        file_name="auth_delay_risk_queue.csv",
        mime="text/csv",
    )

with plan_tab:
    section_header(
        "Plan Intelligence",
        "Optional CPSC analysis for contract and plan-level sales targeting.",
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("CPSC states summarized", whole(cpsc_state["State"].nunique()))
    c2.metric("Top plan lift", whole(cpsc_plan_growth.iloc[0]["absolute_growth"]))
    c3.metric("Plan growth rows", whole(len(cpsc_plan_growth)))

    left, right = st.columns([1, 1])
    with left:
        top_plans = cpsc_plan_growth.head(15).copy()
        top_plans["plan_label"] = top_plans["Contract Number"] + "-" + top_plans["Plan ID"].astype(str)
        fig = px.bar(top_plans, x="plan_label", y="absolute_growth", color="Plan Type", hover_name="Plan Name", title="Top CPSC plans by enrollment lift")
        st.plotly_chart(fig, width="stretch")
    with right:
        fig = px.bar(cpsc_state.head(20), x="State", y="observed_enrollment", title="Latest CPSC enrollment by state")
        st.plotly_chart(fig, width="stretch")

    with st.expander("Open plan growth table"):
        st.dataframe(
            cpsc_plan_growth[
                ["Contract Number", "Plan ID", "Organization Name", "Plan Name", "Plan Type", "last_enrollment", "absolute_growth", "growth_pct"]
            ].head(50),
            width="stretch",
            hide_index=True,
        )
        st.download_button(
            "Download plan intelligence table",
            data=csv_bytes(cpsc_plan_growth),
            file_name="plan_intelligence_growth.csv",
            mime="text/csv",
        )

with validation_tab:
    section_header(
        "Validation & Assumptions",
        "Evidence that the MVP is scoped correctly and does not overclaim public CMS data.",
    )
    st.dataframe(validation, width="stretch", hide_index=True)

    left, right = st.columns([1, 1])
    with left:
        st.markdown("**Data handling policy**")
        st.write("- CMS-suppressed enrollment values are retained and flagged.")
        st.write("- Outliers are flagged, not dropped.")
        st.write("- CPSC is compacted to plan/state-plan level for dashboard use.")
    with right:
        st.markdown("**Scope guardrails**")
        st.write("- Forecast is enrollment-based opportunity forecasting, not provider revenue forecasting.")
        st.write("- No PMPM revenue assumption is used.")
        st.write("- PA and timing outputs are CMS benefit-field exposure scores, not supervised denial or delay predictions.")
    st.download_button(
        "Download validation summary",
        data=csv_bytes(validation),
        file_name="model_validation_summary.csv",
        mime="text/csv",
    )
