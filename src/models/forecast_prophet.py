from __future__ import annotations

import json
from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from src.config import MODEL_DIR, PROCESSED_DIR, TABLE_DIR, ensure_dirs


@dataclass
class ForecastResult:
    forecast: pd.DataFrame
    metrics: pd.DataFrame


def load_national_series() -> pd.DataFrame:
    path = PROCESSED_DIR / "ma_scp_monthly_national.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run notebook 02 or src.data.load_ma_scp first.")
    ts = pd.read_parquet(path).sort_values("report_month")
    return ts[["report_month", "observed_enrollment"]].copy()


def metric_row(model: str, actual: pd.Series, predicted: pd.Series, target: str) -> dict:
    return {
        "model": model,
        "target": target,
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(mean_squared_error(actual, predicted) ** 0.5),
        "mape": float(mean_absolute_percentage_error(actual, predicted)),
        "holdout_months": int(len(actual)),
    }


def baseline_forecasts(ts: pd.DataFrame, target: str, holdout_months: int = 3) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = ts.iloc[:-holdout_months].copy()
    test = ts.iloc[-holdout_months:].copy()
    rows = []
    metrics = []

    naive_pred = pd.Series([train[target].iloc[-1]] * len(test), index=test.index)
    ma3_value = train[target].tail(3).mean()
    ma3_pred = pd.Series([ma3_value] * len(test), index=test.index)
    drift = (train[target].iloc[-1] - train[target].iloc[0]) / max(len(train) - 1, 1)
    drift_pred = pd.Series([train[target].iloc[-1] + drift * i for i in range(1, len(test) + 1)], index=test.index)

    for model, pred in [("naive_last_value", naive_pred), ("moving_average_3m", ma3_pred), ("linear_drift", drift_pred)]:
        metrics.append(metric_row(model, test[target], pred, target))
        rows.append(
            pd.DataFrame(
                {
                    "ds": test["report_month"].values,
                    "actual": test[target].values,
                    "yhat": pred.values,
                    "yhat_lower": pred.values,
                    "yhat_upper": pred.values,
                    "model": model,
                    "target": target,
                    "period_type": "holdout",
                }
            )
        )

    return pd.concat(rows, ignore_index=True), pd.DataFrame(metrics)


def prophet_forecast(ts: pd.DataFrame, target: str, holdout_months: int = 3, future_months: int = 3) -> ForecastResult:
    train = ts.iloc[:-holdout_months].copy()
    test = ts.iloc[-holdout_months:].copy()
    prophet_train = train.rename(columns={"report_month": "ds", target: "y"})[["ds", "y"]]
    model = Prophet(interval_width=0.8, yearly_seasonality=False, weekly_seasonality=False, daily_seasonality=False)
    model.fit(prophet_train)

    future = model.make_future_dataframe(periods=holdout_months + future_months, freq="MS")
    fcst = model.predict(future)[["ds", "yhat", "yhat_lower", "yhat_upper"]]
    fcst["model"] = "prophet"
    fcst["target"] = target
    fcst["period_type"] = np.where(
        fcst["ds"].isin(test["report_month"]),
        "holdout",
        np.where(fcst["ds"] > ts["report_month"].max(), "future", "train"),
    )
    fcst = fcst.merge(test[["report_month", target]].rename(columns={"report_month": "ds", target: "actual"}), on="ds", how="left")
    holdout = fcst[fcst["period_type"].eq("holdout")].copy()
    metrics = pd.DataFrame([metric_row("prophet", holdout["actual"], holdout["yhat"], target)])
    joblib.dump(model, MODEL_DIR / f"prophet_{target}.joblib")
    return ForecastResult(fcst, metrics)


def exp_smoothing_forecast(ts: pd.DataFrame, target: str, holdout_months: int = 3, future_months: int = 3) -> ForecastResult:
    train = ts.iloc[:-holdout_months].copy()
    test = ts.iloc[-holdout_months:].copy()
    model = ExponentialSmoothing(train[target], trend="add", seasonal=None, initialization_method="estimated").fit()
    pred = model.forecast(holdout_months + future_months)
    dates = pd.date_range(test["report_month"].iloc[0], periods=holdout_months + future_months, freq="MS")
    fcst = pd.DataFrame(
        {
            "ds": dates,
            "yhat": pred.values,
            "yhat_lower": pred.values,
            "yhat_upper": pred.values,
            "model": "exp_smoothing",
            "target": target,
        }
    )
    fcst["period_type"] = np.where(fcst["ds"].isin(test["report_month"]), "holdout", "future")
    fcst = fcst.merge(test[["report_month", target]].rename(columns={"report_month": "ds", target: "actual"}), on="ds", how="left")
    holdout = fcst[fcst["period_type"].eq("holdout")]
    metrics = pd.DataFrame([metric_row("exp_smoothing", holdout["actual"], holdout["yhat"], target)])
    joblib.dump(model, MODEL_DIR / f"exp_smoothing_{target}.joblib")
    return ForecastResult(fcst, metrics)


def run_forecasting(targets: tuple[str, ...] = ("observed_enrollment",)) -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_dirs()
    ts = load_national_series()
    all_forecasts = []
    all_metrics = []
    for target in targets:
        baseline_fcst, baseline_metrics = baseline_forecasts(ts, target)
        prophet_result = prophet_forecast(ts, target)
        exp_result = exp_smoothing_forecast(ts, target)
        all_forecasts.extend([baseline_fcst, prophet_result.forecast, exp_result.forecast])
        all_metrics.extend([baseline_metrics, prophet_result.metrics, exp_result.metrics])

    forecasts = pd.concat(all_forecasts, ignore_index=True)
    metrics = pd.concat(all_metrics, ignore_index=True)
    metrics = metrics.sort_values(["target", "mape", "rmse"]).reset_index(drop=True)
    forecasts.to_csv(PROCESSED_DIR / "forecast_results.csv", index=False)
    metrics.to_csv(TABLE_DIR / "forecast_metrics.csv", index=False)
    (TABLE_DIR / "forecast_decision.json").write_text(
        json.dumps(
            {
                "primary_target": "observed_enrollment",
                "decision": "Use the lowest holdout MAPE model for dashboard headline, but show all model metrics.",
                "caveat": "Observed enrollment is forecast as a CMS public-data opportunity signal, not actual provider revenue.",
            },
            indent=2,
        )
    )
    return forecasts, metrics


def main() -> None:
    forecasts, metrics = run_forecasting()
    print(metrics)
    print(f"Wrote {len(forecasts):,} forecast rows.")


if __name__ == "__main__":
    main()
