-- ============================================================
-- 03_recommendations.sql
-- Hospital Readmission Analytics — Business Recommendation Layer
-- Adds recommended_action using SQL CASE logic
-- This moves you from 'analyst who reports' →
-- 'analyst who drives clinical decisions'
-- DEPENDS ON: 02_kpi_view.sql (v_hospital_kpis must exist)
-- ============================================================

DROP VIEW IF EXISTS v_hospital_profile CASCADE;
DROP VIEW IF EXISTS v_hospital_recommendations CASCADE;

CREATE VIEW v_hospital_recommendations AS
SELECT
    facility_id,
    state,
    condition_name,
    measure_name,
    risk_tier,
    penalty_flag,
    readmission_rate,
    penalty_cost,
    risk_score,
    improvement_rate,
    excess_readmission_ratio,
    hospital_rank_in_state,

    -- ── Business Recommendation Layer (SQL CASE logic) ────────
    CASE
        -- HIGH risk — condition-specific urgent actions
        WHEN risk_tier = 'HIGH' AND condition_name = 'Heart Failure'
            THEN 'URGENT: Implement structured 7-day post-discharge phone follow-up. Studies show 20-25% readmission reduction.'

        WHEN risk_tier = 'HIGH' AND condition_name = 'COPD'
            THEN 'URGENT: Add pulmonary rehab referral protocol at discharge. Schedule follow-up within 72 hours.'

        WHEN risk_tier = 'HIGH' AND condition_name = 'Pneumonia'
            THEN 'URGENT: Review antibiotic stewardship protocols. Ensure vaccination status documented at discharge.'

        WHEN risk_tier = 'HIGH' AND condition_name = 'Hip/Knee Replacement'
            THEN 'URGENT: Strengthen post-surgical care coordination. Add physical therapy follow-up within 5 days.'

        WHEN risk_tier = 'HIGH' AND condition_name = 'CABG'
            THEN 'URGENT: Implement cardiac rehab referral at discharge. Schedule cardiology follow-up within 7 days.'

        WHEN risk_tier = 'HIGH' AND condition_name = 'Acute Myocardial Infarction'
            THEN 'URGENT: Ensure dual antiplatelet therapy compliance. Schedule cardiology follow-up within 3 days.'

        -- MEDIUM risk — condition-specific monitoring
        WHEN risk_tier = 'MEDIUM' AND condition_name = 'Heart Failure'
            THEN 'MONITOR: Verify daily weight monitoring education at discharge. Schedule follow-up within 14 days.'

        WHEN risk_tier = 'MEDIUM' AND condition_name = 'COPD'
            THEN 'MONITOR: Ensure inhaler technique education at discharge. Schedule follow-up within 2 weeks.'

        WHEN risk_tier = 'MEDIUM' AND condition_name = 'Pneumonia'
            THEN 'MONITOR: Verify appropriate antibiotic duration. Ensure follow-up chest X-ray scheduled.'

        WHEN risk_tier = 'MEDIUM'
            THEN 'MONITOR: Review discharge planning checklist. Identify high-risk patients for follow-up calls.'

        -- LOW risk — maintenance
        WHEN risk_tier = 'LOW'
            THEN 'MAINTAIN: Current protocols effective. Continue monitoring quarterly. Share best practices.'

        ELSE 'REVIEW: Insufficient data — manual review recommended.'
    END AS recommended_action,

    -- Priority level for filtering and sorting
    CASE
        WHEN risk_tier = 'HIGH'   THEN 1
        WHEN risk_tier = 'MEDIUM' THEN 2
        WHEN risk_tier = 'LOW'    THEN 3
        ELSE 4
    END AS priority_level

FROM v_hospital_kpis;

-- ── Preview: Top 20 highest priority recommendations ──────────
SELECT
    facility_id,
    state,
    condition_name,
    risk_tier,
    ROUND(risk_score::numeric, 1)   AS risk_score,
    ROUND(penalty_cost::numeric, 0) AS penalty_usd,
    recommended_action
FROM v_hospital_recommendations
ORDER BY priority_level ASC, risk_score DESC
LIMIT 20;
