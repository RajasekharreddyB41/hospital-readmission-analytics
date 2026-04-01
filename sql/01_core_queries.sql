-- ============================================================
-- 01_core_queries.sql
-- Hospital Readmission Analytics — Core Business Queries
-- All queries use CTEs and window functions
-- Table: fact_readmissions (11,720 rows)
-- ============================================================

-- ── Q1: Top 10 worst hospitals nationally ────────────────────
-- Business question: Which hospitals have the highest excess
-- readmission ratios and greatest penalty exposure?
WITH ranked_hospitals AS (
    SELECT
        facility_id,
        state,
        condition_name,
        excess_readmission_ratio,
        estimated_penalty_cost,
        RANK() OVER (
            ORDER BY excess_readmission_ratio DESC
        ) AS national_rank
    FROM fact_readmissions
    WHERE excess_readmission_ratio IS NOT NULL
)
SELECT
    national_rank,
    facility_id,
    state,
    condition_name,
    ROUND(excess_readmission_ratio::numeric, 4) AS excess_ratio,
    ROUND(estimated_penalty_cost::numeric, 0)   AS penalty_cost_usd
FROM ranked_hospitals
WHERE national_rank <= 10
ORDER BY national_rank;


-- ── Q2: Worst condition per state ────────────────────────────
-- Business question: Which medical condition drives the most
-- readmissions in each state? Helps target state-level programs.
WITH condition_by_state AS (
    SELECT
        state,
        condition_name,
        ROUND(AVG(excess_readmission_ratio)::numeric, 4) AS avg_ratio,
        COUNT(*) AS hospital_count,
        RANK() OVER (
            PARTITION BY state
            ORDER BY AVG(excess_readmission_ratio) DESC
        ) AS rank_in_state
    FROM fact_readmissions
    WHERE excess_readmission_ratio IS NOT NULL
    GROUP BY state, condition_name
)
SELECT
    state,
    condition_name AS worst_condition,
    avg_ratio,
    hospital_count
FROM condition_by_state
WHERE rank_in_state = 1
ORDER BY avg_ratio DESC;


-- ── Q3: States with most HIGH-risk hospitals ──────────────────
-- Business question: Which states need the most intervention?
-- Used by CMS for resource allocation decisions.
WITH high_risk_by_state AS (
    SELECT
        state,
        COUNT(*) AS high_risk_count,
        ROUND(AVG(excess_readmission_ratio)::numeric, 4) AS avg_ratio,
        ROUND(SUM(estimated_penalty_cost)::numeric, 0)   AS total_penalty_exposure
    FROM fact_readmissions
    WHERE risk_tier = 'HIGH'
    GROUP BY state
    HAVING COUNT(*) >= 1
)
SELECT
    state,
    high_risk_count,
    avg_ratio,
    total_penalty_exposure,
    RANK() OVER (ORDER BY high_risk_count DESC) AS state_rank
FROM high_risk_by_state
ORDER BY high_risk_count DESC
LIMIT 15;


-- ── Q4: National average by condition ────────────────────────
-- Business question: Which conditions are the biggest national
-- problem? What % of hospitals are penalized per condition?
SELECT
    condition_name,
    ROUND(AVG(excess_readmission_ratio)::numeric, 4)  AS national_avg_ratio,
    ROUND(MIN(excess_readmission_ratio)::numeric, 4)  AS best_ratio,
    ROUND(MAX(excess_readmission_ratio)::numeric, 4)  AS worst_ratio,
    COUNT(*)                                           AS total_hospitals,
    SUM(CASE WHEN penalty_flag = true THEN 1 ELSE 0 END) AS hospitals_penalized,
    ROUND(
        100.0 * SUM(CASE WHEN penalty_flag = true THEN 1 ELSE 0 END) / COUNT(*),
        1
    )                                                  AS pct_penalized
FROM fact_readmissions
WHERE excess_readmission_ratio IS NOT NULL
GROUP BY condition_name
ORDER BY national_avg_ratio DESC;


-- ── Q5: Penalty exposure estimate by state ────────────────────
-- Business question: Which states face the largest total
-- CMS penalty bills? Drives policy and funding decisions.
WITH state_penalties AS (
    SELECT
        state,
        COUNT(*)                                              AS total_hospitals,
        SUM(CASE WHEN penalty_flag = true THEN 1 ELSE 0 END) AS penalized_count,
        ROUND(SUM(estimated_penalty_cost)::numeric, 0)        AS total_penalty_usd,
        ROUND(AVG(excess_readmission_ratio)::numeric, 4)      AS avg_ratio
    FROM fact_readmissions
    GROUP BY state
)
SELECT
    state,
    total_hospitals,
    penalized_count,
    total_penalty_usd,
    avg_ratio,
    RANK() OVER (ORDER BY total_penalty_usd DESC) AS penalty_rank
FROM state_penalties
ORDER BY total_penalty_usd DESC
LIMIT 20;


-- ── Q6: Hospital performance distribution ─────────────────────
-- Business question: What's the overall risk landscape?
-- How many hospitals fall in each risk tier?
SELECT
    risk_tier,
    COUNT(*)                                                AS hospital_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)     AS pct_of_total,
    ROUND(AVG(excess_readmission_ratio)::numeric, 4)        AS avg_ratio,
    ROUND(SUM(estimated_penalty_cost)::numeric, 0)          AS total_penalty_usd
FROM fact_readmissions
WHERE risk_tier IS NOT NULL
GROUP BY risk_tier
ORDER BY avg_ratio DESC;
