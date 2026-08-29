# RCM Opportunity Forecasting & Prior Authorization Intelligence
  <img src="./workflow.png" alt="Workflow Diagram" width="100%"/>

## Overview

**RCM Opportunity Forecasting & Prior Authorization Intelligence** is a public CMS-data analytics system designed for Revenue Cycle Management (RCM) teams.

The system analyzes Medicare Advantage enrollment trends, forecasts 90-day enrollment opportunities, identifies prior authorization exposure, evaluates authorization timing exposure, and highlights Medicare Advantage growth opportunities.

The project uses publicly available CMS Medicare Advantage enrollment, penetration, plan, and prior-authorization benefit data. It does not use PHI, synthetic denial labels, or PMPM revenue assumptions.

---

## Aim

- Forecast Medicare Advantage enrollment opportunities for the next 90 days
- Identify enrollment growth opportunities across states, counties, and plans
- Analyze prior authorization exposure using CMS benefit data
- Identify potential authorization timing exposure
- Provide actionable intelligence for RCM teams
- Present results through an interactive dashboard

---

## Key Features

- **90-Day Enrollment Forecast** — Forecasts near-term Medicare Advantage enrollment opportunities
- **Growth Opportunity Analysis** — Identifies growing states, counties, plan types, and plans
- **Prior Authorization Intelligence** — Identifies plans with higher prior authorization exposure
- **Authorization Timing Analysis** — Flags potential timing exposure using CMS timing guardrails
- **Plan Intelligence** — Provides plan-level Medicare Advantage insights
- **Data Validation** — Includes validation and data-quality checks
- **Interactive Dashboard** — Presents insights through a Streamlit dashboard

---

## Benefits

- **Reduces Manual Analysis** — Converts large public CMS datasets into usable insights
- **Supports RCM Strategy** — Helps teams identify potential areas for outreach and prioritization
- **Improves Prioritization** — Highlights plans and markets requiring further attention
- **Provides Early Signals** — Uses enrollment trends to identify emerging opportunities
- **Data-Driven Decisions** — Supports strategic decisions using measurable CMS data
- **Transparent Analysis** — Clearly separates public-data evidence from unsupported revenue or denial claims

---

## Workflow

The system follows this overall process:

**CMS Public Data → Data Processing → EDA & Validation → Enrollment Forecasting → Prior Authorization Analysis → Authorization Timing Analysis → Growth Opportunity Analysis → Streamlit Dashboard**

### Workflow Steps

**1. CMS Data Collection**  
Public Medicare Advantage enrollment, plan, penetration, and benefit data is collected from CMS.

**2. Data Processing**  
The collected data is cleaned, standardized, and prepared for analysis.

**3. EDA & Validation**  
Enrollment trends, geographic patterns, plan information, missing values, and data quality are analyzed.

**4. Enrollment Forecasting**  
Historical Medicare Advantage enrollment is analyzed to generate a **90-day enrollment forecast**.

**5. Prior Authorization Analysis**  
CMS benefit fields are analyzed to identify plans with higher prior authorization exposure and generate prioritization insights.

**6. Authorization Timing Analysis**  
Plans are evaluated against CMS authorization timing guardrails to identify potential timing exposure.

**7. Growth Opportunity Analysis**  
Medicare Advantage growth is analyzed across states, counties, plan types, and plans to identify potential opportunities.

**8. Dashboard**  
The final analytics are presented through an interactive **Streamlit executive dashboard**.

---

## Current Results

- CMS enrollment data covers **January 2024 through May 2026**
- National observed Medicare Advantage enrollment increased from approximately **33.48M to 36.08M**
- Forecast target: **observed enrollment**
- Forecast horizon: **90 days**
- Best-performing holdout model: **Linear Drift**
- Holdout MAPE: approximately **0.048%**
- Prior authorization analysis is based on **CMS PBP benefit fields**
- Authorization timing analysis uses **CMS timing guardrails**

---

## Use Cases

- RCM opportunity identification
- Medicare Advantage market analysis
- Enrollment growth forecasting
- Prior authorization exposure prioritization
- Authorization timing analysis
- Plan-level intelligence
- Geographic growth analysis
- Strategic RCM outreach

---

## Project Goal

The goal of **RCM Opportunity Forecasting & Prior Authorization Intelligence** is to transform public Medicare Advantage data into practical RCM intelligence.

> **Enrollment Trends → Forecasting → Prior Authorization Intelligence → Timing Exposure → Growth Opportunities → RCM Decision Support**

---

## Workflow Diagram

![RCM Opportunity Forecasting & Prior Authorization Intelligence Workflow](docs/workflow.png)
