-- ============================================================
-- 04_analytical_views.sql
-- Hospital Readmission Analytics — Reusable Analytical Views
-- These views power the Tableau dashboard and Streamlit app
-- DEPENDS ON: 02_kpi_view.sql, 03_recommendations.sql
-- ============================================================


-- ── VIEW 1: National summary by condition ─────────────────────
-- Business purpose: Shows which conditions are the biggest
-- national problem — used for Tableau condition breakdown chart
DROP VIEW IF EXISTS v_national_summary CASCADE;

CREATE VIEW v_national_summary AS
SELECT
    condition_name,
    COUNT(*)                                                 AS total_hospitals,
    ROUND(AVG(excess_readmission_ratio)::numeric, 4)         AS national_avg_ratio,
    ROUND(MIN(excess_readmission_ratio)::numeric, 4)         AS best_ratio,
    ROUND(MAX(excess_readmission_ratio)::numeric, 4)         AS worst_ratio,
    SUM(CASE WHEN penalty_flag = true THEN 1 ELSE 0 END)    AS hospitals_penalized,
    ROUND(
        100.0 * SUM(CASE WHEN penalty_flag = true THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0), 1
    )                                                        AS pct_penalized,
    ROUND(SUM(estimated_penalty_cost)::numeric, 0)           AS total_penalty_usd
FROM fact_readmissions
WHERE excess_readmission_ratio IS NOT NULL
GROUP BY condition_name
ORDER BY national_avg_ratio DESC;

SELECT * FROM v_national_summary;


-- ── VIEW 2: State scorecard ───────────────────────────────────
-- Business purpose: State-level executive summary
-- Used for Tableau US heatmap
DROP VIEW IF EXISTS v_state_scorecard CASCADE;

CREATE VIEW v_state_scorecard AS
SELECT
    state,
    COUNT(DISTINCT facility_id)                              AS unique_hospitals,
    COUNT(*)                                                 AS total_records,
    ROUND(AVG(excess_readmission_ratio)::numeric, 4)         AS avg_ratio,
    SUM(CASE WHEN risk_tier = 'HIGH'   THEN 1 ELSE 0 END)   AS high_risk_count,
    SUM(CASE WHEN risk_tier = 'MEDIUM' THEN 1 ELSE 0 END)   AS medium_risk_count,
    SUM(CASE WHEN risk_tier = 'LOW'    THEN 1 ELSE 0 END)   AS low_risk_count,
    SUM(CASE WHEN penalty_flag = true  THEN 1 ELSE 0 END)   AS hospitals_penalized,
    ROUND(SUM(estimated_penalty_cost)::numeric, 0)           AS total_penalty_usd,
    RANK() OVER (ORDER BY AVG(excess_readmission_ratio) DESC) AS state_rank
FROM fact_readmissions
WHERE excess_readmission_ratio IS NOT NULL
GROUP BY state;

SELECT * FROM v_state_scorecard ORDER BY state_rank LIMIT 15;


-- ── VIEW 3: High risk hospitals (for executive alerts) ────────
-- Business purpose: Filtered list of hospitals needing
-- immediate intervention — used in Streamlit app and AI layer
DROP VIEW IF EXISTS v_high_risk_hospitals CASCADE;

CREATE VIEW v_high_risk_hospitals AS
SELECT
    facility_id,
    state,
    condition_name,
    ROUND(excess_readmission_ratio::numeric, 4) AS excess_ratio,
    ROUND(estimated_penalty_cost::numeric, 0)   AS penalty_usd,
    hospital_rank_in_state,
    risk_tier,
    ROUND(deviation_from_national::numeric, 4)  AS deviation_from_national
FROM fact_readmissions
WHERE risk_tier = 'HIGH'
ORDER BY estimated_penalty_cost DESC;

SELECT COUNT(*) AS high_risk_hospital_count FROM v_high_risk_hospitals;
SELECT * FROM v_high_risk_hospitals LIMIT 10;


-- ── VIEW 4: Hospital full profile (for Streamlit search) ──────
-- Business purpose: Complete profile for one hospital lookup
-- Joins KPIs + recommendations for the Streamlit app
DROP VIEW IF EXISTS v_hospital_profile CASCADE;

CREATE VIEW v_hospital_profile AS
SELECT
    f.facility_id,
    f.state,
    f.condition_name,
    f.measure_name,
    f.risk_tier,
    f.penalty_flag,
    ROUND(f.excess_readmission_ratio::numeric, 4)   AS excess_ratio,
    ROUND(f.predicted_readmission_rate::numeric, 2)  AS predicted_rate,
    ROUND(f.expected_readmission_rate::numeric, 2)   AS expected_rate,
    ROUND(f.deviation_from_national::numeric, 4)     AS deviation_from_national,
    ROUND(f.state_avg_ratio::numeric, 4)             AS state_avg_ratio,
    f.hospital_rank_in_state,
    ROUND(f.estimated_penalty_cost::numeric, 0)      AS penalty_usd,
    k.readmission_rate,
    k.risk_score,
    k.improvement_rate,
    r.recommended_action
FROM fact_readmissions f
LEFT JOIN v_hospital_kpis k
    ON f.facility_id = k.facility_id
    AND f.measure_name = k.measure_name
LEFT JOIN v_hospital_recommendations r
    ON f.facility_id = r.facility_id
    AND f.measure_name = r.measure_name
WHERE f.excess_readmission_ratio IS NOT NULL;

-- Test: Look up a specific hospital by facility_id
SELECT * FROM v_hospital_profile WHERE facility_id = 10001 LIMIT 5;

-- Test: Count total profiles
SELECT COUNT(*) AS total_profiles FROM v_hospital_profile;
