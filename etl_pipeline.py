"""
etl_pipeline.py
===============
Step 4 — ETL Pipeline + Feature Engineering
Clean the raw data, engineer analytical columns, load to PostgreSQL.

Usage:
    python etl_pipeline.py
"""

import os
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from datetime import datetime

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
RAW_FILE       = os.path.join("data", "raw", "readmissions_raw.csv")
CLEAN_FILE     = os.path.join("data", "processed", "readmissions_clean.csv")
FEATURES_FILE  = os.path.join("data", "processed", "readmissions_features.csv")
DB_URL         = os.getenv("DATABASE_URL", "")

# Condition code → readable name mapping
CONDITION_MAP = {
    "READM-30-HF-HRRP"      : "Heart Failure",
    "READM-30-PN-HRRP"      : "Pneumonia",
    "READM-30-COPD-HRRP"    : "COPD",
    "READM-30-HIP-KNEE-HRRP": "Hip/Knee Replacement",
    "READM-30-CABG-HRRP"    : "CABG",
    "READM-30-AMI-HRRP"     : "AMI (Heart Attack)",
}

def log(msg=""):
    print(msg)

def section(title):
    log(f"\n{'='*60}")
    log(f"  {title}")
    log(f"{'='*60}")

# ─────────────────────────────────────────────────────────────────────────────
# PART 1 — DATA CLEANING
# ─────────────────────────────────────────────────────────────────────────────
section("PART 1 — Data Cleaning")

log("Loading raw data...")
df = pd.read_csv(RAW_FILE, encoding="utf-8-sig")
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
log(f"Raw rows loaded : {len(df):,}")

# Step 1: Drop rows where excess_readmission_ratio is null
# These hospitals have too few cases for CMS to calculate a ratio
before = len(df)
df = df[df["excess_readmission_ratio"].notna()].copy()
df["excess_readmission_ratio"] = pd.to_numeric(
    df["excess_readmission_ratio"], errors="coerce"
)
df = df[df["excess_readmission_ratio"].notna()].copy()
log(f"Dropped null ratio rows : {before - len(df):,}")
log(f"Remaining rows          : {len(df):,}")

# Step 2: Standardize facility_name
df["facility_name"] = df["facility_name"].str.strip().str.title()

# Step 3: Cast numeric columns
for col in ["predicted_readmission_rate", "expected_readmission_rate",
            "number_of_discharges"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Step 4: Handle number_of_readmissions — mixed type column
df["number_of_readmissions"] = pd.to_numeric(
    df["number_of_readmissions"], errors="coerce"
)

# Step 5: Parse dates
df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
df["end_date"]   = pd.to_datetime(df["end_date"],   errors="coerce")

# Step 6: Drop footnote column — not analytically useful
df = df.drop(columns=["footnote"], errors="ignore")

# Step 7: Add readable condition name
df["condition_name"] = df["measure_name"].map(CONDITION_MAP)

log(f"\nCleaning complete.")
log(f"Final clean rows : {len(df):,}")
log(f"Columns          : {list(df.columns)}")

# Save clean file
os.makedirs("data/processed", exist_ok=True)
df.to_csv(CLEAN_FILE, index=False)
log(f"Saved to         : {CLEAN_FILE}")

# ─────────────────────────────────────────────────────────────────────────────
# PART 2 — FEATURE ENGINEERING
# ─────────────────────────────────────────────────────────────────────────────
section("PART 2 — Feature Engineering")

# Feature 1: risk_tier
df["risk_tier"] = pd.cut(
    df["excess_readmission_ratio"],
    bins=[0, 1.0, 1.2, float("inf")],
    labels=["LOW", "MEDIUM", "HIGH"],
    right=True
)
risk_counts = df["risk_tier"].value_counts()
log("risk_tier distribution:")
for tier, cnt in risk_counts.items():
    log(f"  {tier:8} : {cnt:,}")

# Feature 2: deviation_from_national
# Positive = worse than average, Negative = better than average
df["deviation_from_national"] = (
    df["excess_readmission_ratio"] - 1.0
).round(4)

# Feature 3: penalty_flag
df["penalty_flag"] = df["excess_readmission_ratio"] > 1.0
log(f"\npenalty_flag = True  : {df['penalty_flag'].sum():,} hospitals penalized")
log(f"penalty_flag = False : {(~df['penalty_flag']).sum():,} hospitals not penalized")

# Feature 4: state_avg_ratio — average ratio per state per condition
df["state_avg_ratio"] = df.groupby(
    ["state", "measure_name"]
)["excess_readmission_ratio"].transform("mean").round(4)

# Feature 5: hospital_rank_in_state
# Rank 1 = worst in state for that condition
df["hospital_rank_in_state"] = df.groupby(
    ["state", "measure_name"]
)["excess_readmission_ratio"].rank(
    method="dense", ascending=False
).astype(int)

# Feature 6: deviation_from_state_avg
df["deviation_from_state_avg"] = (
    df["excess_readmission_ratio"] - df["state_avg_ratio"]
).round(4)

# Feature 7: estimated_penalty_cost
# CMS baseline: $564M total / 11,720 penalized hospitals ≈ $48,122 per hospital
# Scaled by how much above average the ratio is
CMS_TOTAL_PENALTY = 564_000_000
penalized_count   = df["penalty_flag"].sum()
base_per_hospital = CMS_TOTAL_PENALTY / max(penalized_count, 1)

df["estimated_penalty_cost"] = df.apply(
    lambda row: round(
        base_per_hospital * (row["excess_readmission_ratio"] - 1.0), 2
    ) if row["penalty_flag"] else 0.0,
    axis=1
)

total_estimated = df["estimated_penalty_cost"].sum()
log(f"\nestimated_penalty_cost:")
log(f"  Total estimated exposure : ${total_estimated:,.0f}")
log(f"  Avg per penalized hosp.  : ${df[df['penalty_flag']]['estimated_penalty_cost'].mean():,.0f}")
log(f"  Max single hospital      : ${df['estimated_penalty_cost'].max():,.0f}")

log("\nFeature engineering complete.")
log(f"New columns added: risk_tier, deviation_from_national, penalty_flag,")
log(f"  state_avg_ratio, hospital_rank_in_state, deviation_from_state_avg,")
log(f"  estimated_penalty_cost")

# Save features file
df.to_csv(FEATURES_FILE, index=False)
log(f"\nSaved to: {FEATURES_FILE}")

# ─────────────────────────────────────────────────────────────────────────────
# PART 3 — LOAD TO POSTGRESQL
# ─────────────────────────────────────────────────────────────────────────────
section("PART 3 — Load to PostgreSQL")

if not DB_URL:
    log("WARNING: DATABASE_URL not set in .env file.")
    log("Skipping PostgreSQL load — CSV files saved successfully.")
    log("\nTo load to PostgreSQL:")
    log("  1. Set DATABASE_URL in your .env file")
    log("  2. Run: python etl_pipeline.py")
else:
    try:
        log(f"Connecting to PostgreSQL...")
        engine = create_engine(DB_URL)

        with engine.connect() as conn:
            # Create schema
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS dim_hospital (
                    hospital_id   SERIAL PRIMARY KEY,
                    facility_id   INTEGER UNIQUE NOT NULL,
                    facility_name TEXT,
                    state         VARCHAR(2)
                );
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS dim_condition (
                    condition_id   SERIAL PRIMARY KEY,
                    measure_name   TEXT UNIQUE NOT NULL,
                    condition_name TEXT
                );
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS fact_readmissions (
                    id                        SERIAL PRIMARY KEY,
                    facility_id               INTEGER,
                    measure_name              TEXT,
                    state                     VARCHAR(2),
                    excess_readmission_ratio  FLOAT,
                    predicted_readmission_rate FLOAT,
                    expected_readmission_rate  FLOAT,
                    number_of_discharges       FLOAT,
                    number_of_readmissions     FLOAT,
                    risk_tier                 TEXT,
                    deviation_from_national   FLOAT,
                    penalty_flag              BOOLEAN,
                    state_avg_ratio           FLOAT,
                    hospital_rank_in_state    INTEGER,
                    deviation_from_state_avg  FLOAT,
                    estimated_penalty_cost    FLOAT,
                    condition_name            TEXT,
                    start_date                DATE,
                    end_date                  DATE
                );
            """))
            conn.commit()
            log("Tables created (or already exist).")

        # Load fact table
        load_cols = [
            "facility_id", "measure_name", "state",
            "excess_readmission_ratio", "predicted_readmission_rate",
            "expected_readmission_rate", "number_of_discharges",
            "number_of_readmissions", "risk_tier", "deviation_from_national",
            "penalty_flag", "state_avg_ratio", "hospital_rank_in_state",
            "deviation_from_state_avg", "estimated_penalty_cost",
            "condition_name", "start_date", "end_date"
        ]

        df_load = df[[c for c in load_cols if c in df.columns]].copy()
        df_load["risk_tier"] = df_load["risk_tier"].astype(str)

        df_load.to_sql(
            "fact_readmissions",
            engine,
            if_exists="replace",
            index=False,
            chunksize=500
        )
        log(f"Loaded {len(df_load):,} rows into fact_readmissions.")

        # Verify
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM fact_readmissions")
            )
            count = result.fetchone()[0]
            log(f"Verified: {count:,} rows in fact_readmissions table.")

        log("\nPostgreSQL load complete!")

    except Exception as e:
        log(f"\nPostgreSQL error: {e}")
        log("CSV files are saved and ready.")
        log("Fix your DATABASE_URL in .env and re-run to load to PostgreSQL.")

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
section("ETL SUMMARY")
log(f"  Raw rows            : 18,330")
log(f"  After cleaning      : {len(df):,}")
log(f"  Dropped (null ratio): {18330 - len(df):,}")
log(f"  Features added      : 7")
log(f"  Clean CSV saved     : {CLEAN_FILE}")
log(f"  Features CSV saved  : {FEATURES_FILE}")

