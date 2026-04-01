-- ============================================================
-- 02_kpi_view.sql
-- Hospital Readmission Analytics — KPI Metrics Layer
-- Creates v_hospital_kpis view with 4 business KPIs
-- Resume: 'Designed KPI layer tracking $35M+ CMS penalty
--   exposure across 3,000+ hospitals'
-- ============================================================

DROP VIEW IF EXISTS v_hospital_recommendations CASCADE;
DROP VIEW IF EXISTS v_hospital_profile CASCADE;
DROP VIEW IF EXISTS v_hospital_kpis CASCADE;

CREATE VIEW v_hospital_kpis AS
WITH national_avg AS (
    SELECT
        condition_name,
        AVG(excess_readmission_ratio) AS nat_avg_ratio
    FROM fact_readmissions
    WHERE excess_readmission_ratio IS NOT NULL
    GROUP BY condition_name
)
SELECT
    f.facility_id,
    f.state,
    f.condition_name,
    f.measure_name,
    f.risk_tier,
    f.penalty_flag,
    f.hospital_rank_in_state,
    f.excess_readmission_ratio,
    f.predicted_readmission_rate,
    f.expected_readmission_rate,
    f.deviation_from_national,
    f.state_avg_ratio,
    f.estimated_penalty_cost,

    -- KPI 1: readmission_rate (% vs national average)
    ROUND(
        ((f.excess_readmission_ratio / NULLIF(n.nat_avg_ratio, 0)) * 100)::numeric,
        2
    ) AS readmission_rate,

    -- KPI 2: penalty_cost (estimated CMS fine in USD)
    ROUND(f.estimated_penalty_cost::numeric, 2) AS penalty_cost,

    -- KPI 3: risk_score (composite 0-100, higher = worse)
    ROUND(
        LEAST(
            GREATEST(
                (((f.excess_readmission_ratio - 0.4) / (1.6 - 0.4)) * 100)::numeric,
                0
            ),
            100
        ),
        1
    ) AS risk_score,

    -- KPI 4: improvement_rate (predicted vs expected, negative = better)
    ROUND(
        (CASE
            WHEN f.expected_readmission_rate > 0 THEN
                ((f.predicted_readmission_rate - f.expected_readmission_rate)
                 / f.expected_readmission_rate) * 100
            ELSE NULL
        END)::numeric,
        2
    ) AS improvement_rate

FROM fact_readmissions f
LEFT JOIN national_avg n
    ON f.condition_name = n.condition_name
WHERE f.excess_readmission_ratio IS NOT NULL;

-- Verify
SELECT COUNT(*) AS total_rows_in_kpi_view FROM v_hospital_kpis;

-- Preview top 10 highest risk
SELECT
    facility_id,
    state,
    condition_name,
    risk_tier,
    readmission_rate,
    penalty_cost,
    risk_score,
    improvement_rate,
    ROUND(excess_readmission_ratio::numeric, 4) AS excess_ratio
FROM v_hospital_kpis
ORDER BY risk_score DESC
LIMIT 10;
