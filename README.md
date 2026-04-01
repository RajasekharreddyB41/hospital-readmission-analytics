# 🏥 Hospital Readmission Risk Analytics

**End-to-end Healthcare Analytics Pipeline** tracking CMS penalty exposure, risk scores, and AI-generated clinical recommendations across 3,000+ U.S. hospitals.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://hospital-readmission-analytics-rs06.streamlit.app/)
[![Tableau Dashboard](https://img.shields.io/badge/Tableau-Live_Dashboard-blue?logo=tableau)](https://public.tableau.com/app/profile/rajasekhar.reddy.byreddy/viz/HospitalReadmissionRiskAnalytics/HospitalReadmissionDashboard)

---

## Business Problem

CMS penalized hospitals **$564 million** in FY2023 through the Hospital Readmissions Reduction Program for excess readmissions. This project identifies which hospitals are at highest risk, quantifies their penalty exposure, and generates actionable clinical recommendations — the kind of analysis a healthcare data analyst delivers daily.

---

## Pipeline Architecture

```
CMS Dataset (18,330 rows)
    │
    ▼
Python ETL Pipeline ──► Data Quality Checks (7 validations)
    │
    ▼
PostgreSQL Database ──► 6 SQL Views (KPIs + Recommendations)
    │
    ├──► Tableau Public Dashboard (3-view executive dashboard)
    ├──► Power BI Report (4 KPI cards + slicers)
    └──► Streamlit App + Groq AI (live insight generator)
```

---

## Key Findings

- **$35M+ total estimated penalty exposure** across 2,833 hospitals in the dataset
- **Hip/Knee Replacement** is the highest-risk condition with the most HIGH-tier hospitals
- **213 hospitals (1.8%)** flagged as HIGH risk, yet they account for a disproportionate share of penalty costs
- **Southern and Southeastern states** show consistently higher readmission ratios than the national average

---

## KPI Metrics Layer

| KPI | Formula | Business Meaning |
|-----|---------|-----------------|
| **Readmission Rate** | ratio / national_avg × 100 | How far above/below average |
| **Penalty Cost** | excess_ratio × CMS baseline | Estimated CMS fine exposure ($) |
| **Risk Score** | Normalized composite 0–100 | Overall risk ranking |
| **Improvement Rate** | (predicted - expected) / expected × 100 | Performance vs. expectation |

---

## Business Recommendation Layer (SQL CASE Logic)

The pipeline generates **condition-specific clinical recommendations** using SQL CASE logic — no ML needed, pure business rules:

| Risk Tier | Condition | Recommended Action |
|-----------|-----------|-------------------|
| HIGH | Heart Failure | Implement structured 7-day post-discharge phone follow-up |
| HIGH | COPD | Add pulmonary rehab referral protocol at discharge |
| HIGH | Pneumonia | Review antibiotic stewardship protocols |
| MEDIUM | Any | Review discharge planning checklist |
| LOW | Any | Maintain current protocols — monitor quarterly |

---

## AI-Generated Insight (Groq LLM)

The AI layer processes the top 50 high-risk hospitals and generates consulting-level outputs:

**Example Output:**

> **Insight:** This facility shows an excess readmission ratio of 1.63 for Hip/Knee Replacement, placing it significantly above the national average with a risk score of 100/100. The estimated penalty cost of $62,937 highlights the urgent need for targeted intervention.
>
> **Recommendation:** Implement a structured post-surgical care coordination protocol including mandatory physical therapy follow-up within 5 days of discharge and daily patient check-ins during the first week post-surgery.

---

## Live Links

| Resource | URL |
|----------|-----|
| **Streamlit App** | [hospital-readmission-analytics-rs06.streamlit.app](https://hospital-readmission-analytics-rs06.streamlit.app/) |
| **Tableau Dashboard** | [Tableau Public](https://public.tableau.com/app/profile/rajasekhar.reddy.byreddy/viz/HospitalReadmissionRiskAnalytics/HospitalReadmissionDashboard) |
| **GitHub Repo** | [github.com/RajasekharreddyB41/hospital-readmission-analytics](https://github.com/RajasekharreddyB41/hospital-readmission-analytics) |

---

## Tech Stack

| Layer | Tools |
|-------|-------|
| **ETL & Data Quality** | Python, Pandas, NumPy |
| **Database** | PostgreSQL 18, SQLAlchemy |
| **SQL Analysis** | CTEs, Window Functions (RANK, LAG), CASE logic |
| **Dashboards** | Tableau Public, Power BI Desktop (DAX) |
| **AI Layer** | Groq API (LLaMA 3.1), Prompt Engineering |
| **Web App** | Streamlit |
| **Version Control** | Git, GitHub |

---

## Project Structure

```
hospital-readmission-analytics/
├── data/
│   ├── raw/                    # Original CMS dataset
│   └── processed/              # Clean + feature-engineered CSVs
├── sql/
│   ├── 01_core_queries.sql     # 6 business queries (CTEs + window functions)
│   ├── 02_kpi_view.sql         # v_hospital_kpis (4 KPI metrics)
│   ├── 03_recommendations.sql  # v_hospital_recommendations (CASE logic)
│   └── 04_analytical_views.sql # National summary, state scorecard, high-risk list
├── dashboard/
│   ├── hospital_kpis.csv       # Exported view for Tableau/Power BI
│   ├── state_scorecard.csv     # State-level summary
│   ├── national_summary.csv    # Condition-level summary
│   └── hospital_recommendations.csv
├── reports/
│   ├── ai_hospital_insights.csv    # AI-generated insights for 50 hospitals
│   └── ai_output_examples.txt     # 3 sample AI outputs
├── etl_pipeline.py             # Full ETL: clean → engineer → load to PostgreSQL
├── ai_insights.py              # Groq LLM batch insight generator
├── streamlit_app.py            # Interactive web app
├── requirements.txt
└── README.md
```

---

## How to Run Locally

```bash
# Clone the repo
git clone https://github.com/RajasekharreddyB41/hospital-readmission-analytics.git
cd hospital-readmission-analytics

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
echo "DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/healthcare_analytics" > .env
echo "GROQ_API_KEY=your_groq_key_here" >> .env

# Run ETL pipeline
python etl_pipeline.py

# Run SQL views (requires psql)
psql -U postgres -d healthcare_analytics -f sql/02_kpi_view.sql
psql -U postgres -d healthcare_analytics -f sql/03_recommendations.sql
psql -U postgres -d healthcare_analytics -f sql/04_analytical_views.sql

# Generate AI insights
python ai_insights.py

# Launch Streamlit app
streamlit run streamlit_app.py
```

---

## Data Source

[CMS Hospital Readmissions Reduction Program](https://data.cms.gov) — FY2026 public dataset (18,330 rows, 12 columns, 2,995 unique hospitals across 51 states).

---

## Author

**Rajasekhar Reddy Byreddy**
Generative AI Engineer | MS Data Science, New England College

- GitHub: [github.com/RajasekharreddyB41](https://github.com/RajasekharreddyB41)
- LinkedIn: [linkedin.com/in/rajasekhar-reddy-byreddy-552165360](https://linkedin.com/in/rajasekhar-reddy-byreddy-552165360)
- Email: rajasekharreddyb46@gmail.com
