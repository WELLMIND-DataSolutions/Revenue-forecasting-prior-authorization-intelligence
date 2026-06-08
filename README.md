# Revenue Forecasting & Prior Authorization Intelligence

Public CMS-data MVP for RCM teams that need a 90-day revenue-opportunity forecast, prior authorization denial-risk triage, auth delay flags, and Medicare Advantage growth opportunity analytics.

The project uses public CMS Medicare Advantage enrollment, plan, and prior-authorization policy/reporting sources. Revenue is modeled as an enrollment-based opportunity proxy, not actual collections, remit, or claim payment forecasting.

## What the Project Does

This project builds an end-to-end analytics MVP for revenue cycle management teams. It downloads public CMS Medicare Advantage data, prepares modeling-ready enrollment tables, runs EDA, evaluates forecasting models, creates prior authorization and delay-risk scoring demos, and serves the results in a Streamlit executive dashboard.

Main outputs:

- 90-day enrollment and proxy revenue opportunity forecast.
- Growth opportunity analytics by state, county, plan type, and optional CPSC plan data.
- Prior authorization risk queue with documentation-strengthening recommendations.
- Auth delay risk queue based on CMS timing expectations.
- Validation tables, notebooks, and dashboard-ready exports.

## Why the Project Is Useful

RCM teams need early signals before revenue or authorization problems become operational bottlenecks. This MVP shows how public CMS data can support sales and strategy conversations without using PHI, gated payer files, or client-specific claims data.

It is useful because it:

- Turns fragmented public CMS files into a reproducible analytics pipeline.
- Separates actual public-data evidence from proxy assumptions.
- Shows which geographies and plan types are growing.
- Gives a practical first version of PA denial-risk and delay-risk prioritization.
- Documents limitations clearly so reviewers know what can and cannot be claimed.

## How Users Can Get Started

Quick start on Windows PowerShell:

```powershell
git clone https://github.com/WELLMIND-DataSolutions/Revenue-forecasting-prior-authorization-intelligence.git
cd Revenue-forecasting-prior-authorization-intelligence
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r .\requirements.txt
python -m pip install -r .\requirements-optional.txt
.\scripts\download_data.ps1
.\scripts\download_optional_data.ps1
.\scripts\run_pipeline.ps1
.\scripts\run_dashboard.ps1
```

Then open:

```text
http://127.0.0.1:8501
```

For notebook review, start Jupyter with:

```powershell
.\scripts\start_jupyter.ps1
```

## Where Users Can Get Help

Use these project files first:

- `README.md`: setup, install, run, dashboard, and repository structure.
- `RND.md`: research decisions, modeling choices, assumptions, experiments, and limitations.
- `PPT.md`: presentation-ready high-level summary.
- `docs/dataset_register.md`: dataset list and source notes.
- `docs/assumptions.md`: modeling and business assumptions.
- `docs/validation_checklist.md`: validation checklist.
- `docs/02_ma_enrollment_eda_visual_report.md`: GitHub-readable EDA report with static graphs.

If something fails locally, check:

- Whether `.venv` is activated.
- Whether data scripts have downloaded files into `data/raw/`.
- Whether `.\scripts\run_pipeline.ps1` has created `data/processed/` and `reports/tables/`.
- Whether Streamlit is running at `http://127.0.0.1:8501`.

For repository collaboration, open a GitHub issue or contact the maintainers/contributors listed below.

## Who Maintains and Contributes

Maintained by:

- WELLMIND DataSolutions project team.
- Shahneela Zafar / project contributor.

Contributions can include:

- Data-source updates.
- Modeling improvements.
- Dashboard improvements.
- Documentation fixes.
- Validation and testing additions.

Before contributing, keep the core guardrail: do not overclaim public CMS data as actual provider collections, remits, or payer-specific PA outcomes.

## Repository File Guide

| File | Audience | Tells |
| --- | --- | --- |
| `README.md` | User / Developer | How to set up, install, run the pipeline, launch dashboard, and understand repo structure. |
| `RND.md` | Interviewer / Reviewer / Researcher | How the project was built, why decisions were made, what experiments were run, and what limitations exist. |
| `PPT.md` | Presentation audience | High-level slide-style project summary for demo, viva, stakeholder review, or pitch. |

## Business Objective

Client hook:

> We tell you what next month's collections opportunity may look like and which prior authorization requests are likely to get denied or delayed, so the team can strengthen documentation before submission.

MVP deliverables covered:

- Forecast dashboard with CMS trend lines and 90-day projection.
- Prior authorization risk queue with documentation recommendations.
- Auth delay risk table for high-delay procedure-payer combinations.
- Growth opportunity report by geography and plan.
- Validation summary with assumptions, model metrics, and public-data guardrails.

RCM problems covered:

- Prior auth prediction
- Auth delay risk
- Revenue forecasting
- Growth opportunity analytics

## Current Results

- CMS enrollment data window: January 2024 through May 2026.
- National observed MA enrollment increased from about 33.48M to 36.08M.
- Forecast target: `observed_enrollment`.
- Revenue proxy: `proxy_revenue = observed_enrollment * 115 PMPM`.
- Best forecast model on 3-month holdout: `linear_drift`.
- Observed-enrollment holdout MAPE: about `0.048%`.
- PA demo model accuracy: about `93.3%`.
- Auth delay module flags high-risk combinations before submission.
- Suppressed CMS rows are retained and flagged instead of dropped.
- Outliers are flagged for review instead of removed.

## Project Structure

```text
rcm-cms-mvp/
  docs/
    assumptions.md
    dataset_register.md
    validation_checklist.md
  notebooks/
    01_data_inventory_and_quality.ipynb
    02_ma_enrollment_eda.ipynb
    03_revenue_opportunity_forecasting.ipynb
    04_cpsc_plan_level_analysis.ipynb
    05_prior_auth_risk_scoring_demo.ipynb
    06_model_evaluation_and_validation.ipynb
    07_dashboard_export_assets.ipynb
  scripts/
    download_data.ps1
    download_optional_data.ps1
    run_pipeline.ps1
    run_dashboard.ps1
    start_jupyter.ps1
  src/
    config.py
    data/
    dashboard/
    models/
  README.md
  RND.md
  PPT.md
  requirements.txt
  requirements-optional.txt
```

Generated local folders such as `data/raw/`, `data/processed/`, `reports/tables/`, `reports/figures/`, `models/`, `.venv/`, and logs are intentionally ignored by Git.

## Setup

From the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r .\requirements.txt
python -m pip install -r .\requirements-optional.txt
```

`requirements-optional.txt` contains TensorFlow for optional LSTM experimentation. The core MVP runs without depending on LSTM as the headline model.

## Download Data

```powershell
.\scripts\download_data.ps1
.\scripts\download_optional_data.ps1
```

Core sources include:

- CMS Medicare Advantage state/county penetration files.
- CMS MA plan directory.
- CMS PBP benefits JSON.
- CMS prior authorization reporting template and CMS-0057-F related material.
- CMS MA step therapy memo.
- Monthly MA state/county/plan-type enrollment from January 2024 through May 2026.

Optional source:

- CPSC monthly enrollment by contract, plan, state, and county for plan-level growth intelligence.

## Run Pipeline

```powershell
.\scripts\run_pipeline.ps1
```

The pipeline runs:

- MA enrollment ingestion and quality processing.
- Forecast model training/evaluation.
- Prior authorization risk scoring demo.
- Auth delay risk scoring.
- Validation summary generation.

## Run Dashboard

```powershell
.\scripts\run_dashboard.ps1
```

Open:

```text
http://127.0.0.1:8501
```

Dashboard sections:

- Executive View
- 90-Day Forecast
- Growth Opportunity
- Prior Auth Intelligence
- Auth Delay Risk
- Plan Intelligence
- Validation

## Notebooks

| Notebook | Purpose |
| --- | --- |
| `01_data_inventory_and_quality.ipynb` | Data inventory, source checks, file coverage, and quality gate. |
| `02_ma_enrollment_eda.ipynb` | Deep EDA with missing value, duplicate, suppression, outlier, trend, and geography analysis. |
| `03_revenue_opportunity_forecasting.ipynb` | Forecast modeling, holdout evaluation, and 90-day projection logic. |
| `04_cpsc_plan_level_analysis.ipynb` | Contract/plan/state analysis for sales-targeting intelligence. |
| `05_prior_auth_risk_scoring_demo.ipynb` | CMS-aligned PA denial-risk scoring prototype. |
| `06_model_evaluation_and_validation.ipynb` | Model validation, assumptions, limitations, and final decision table. |
| `07_dashboard_export_assets.ipynb` | Dashboard-ready tables and evidence assets. |

GitHub sometimes does not render the full `02_ma_enrollment_eda.ipynb` notebook because it is output-heavy. Use the rendered EDA report instead:

- [`docs/02_ma_enrollment_eda_visual_report.md`](docs/02_ma_enrollment_eda_visual_report.md): GitHub-readable EDA report with 28 static graphs and explanations.

## Dashboard Notes

The Streamlit dashboard is not just a pipeline output viewer. It is organized around the original business deliverables:

- What will the next 90 days look like?
- Which markets are growing?
- Which PA requests need stronger documentation?
- Which requests may be delayed?
- Which plan/geography combinations are useful for sales conversations?
- What should reviewers trust, and what should they not overclaim?

## Limitations

- Public CMS files do not contain provider-specific collections, remits, denials, or request-level prior authorization outcomes.
- The revenue number is a transparent PMPM opportunity proxy.
- PA prediction is a demo risk-prioritization model, not a production payer-specific denial model.
- Forecast history is short, so simple baselines can outperform heavier models.
- CMS-suppressed values are not imputed into false precision.

## Git Workflow

```powershell
git status
git add .
git commit -m "Update dashboard and project documentation"
git push
```
