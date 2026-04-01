"""
eda.py
======
Step 2 — Exploratory Data Analysis
Understand the dataset before writing a single line of ETL.

Usage:
    python eda.py
"""

import os
import pandas as pd
import numpy as np

# ── Load data ─────────────────────────────────────────────────────────────────
RAW_FILE = os.path.join("data", "raw", "readmissions_raw.csv")
REPORT_FILE = os.path.join("reports", "eda_summary.txt")

print("=" * 60)
print("  Hospital Readmission Analytics — Step 2: EDA")
print("=" * 60)

df = pd.read_csv(RAW_FILE, encoding="utf-8-sig")

# Standardize column names — strip spaces, lowercase with underscores
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

print(f"\nDataset loaded: {df.shape[0]:,} rows x {df.shape[1]} columns")

# ── 1. Basic info ─────────────────────────────────────────────────────────────
print("\n--- Column Names & Data Types ---")
print(df.dtypes.to_string())

# ── 2. Missing values ─────────────────────────────────────────────────────────
print("\n--- Missing Values ---")
missing = df.isnull().sum()
missing_pct = (missing / len(df) * 100).round(2)
missing_df = pd.DataFrame({
    "missing_count": missing,
    "missing_pct": missing_pct
})
print(missing_df[missing_df["missing_count"] > 0].to_string())

# ── 3. Unique hospitals ───────────────────────────────────────────────────────
print(f"\n--- Unique Counts ---")
print(f"Unique hospitals : {df['facility_name'].nunique():,}")
print(f"Unique states    : {df['state'].nunique():,}")
print(f"Unique measures  : {df['measure_name'].nunique():,}")

# ── 4. Conditions (measure names) ─────────────────────────────────────────────
print("\n--- Conditions in Dataset (measure_name) ---")
condition_counts = df["measure_name"].value_counts()
print(condition_counts.to_string())

# ── 5. Excess readmission ratio analysis ─────────────────────────────────────
print("\n--- Excess Readmission Ratio Analysis ---")

# Convert to numeric — some rows have 'Not Available'
df["excess_readmission_ratio"] = pd.to_numeric(
    df["excess_readmission_ratio"], errors="coerce"
)

ratio_stats = df["excess_readmission_ratio"].describe()
print(ratio_stats.round(4).to_string())

above_1 = (df["excess_readmission_ratio"] > 1.0).sum()
total_valid = df["excess_readmission_ratio"].notna().sum()
pct_above = (above_1 / total_valid * 100).round(1)

print(f"\nHospitals ABOVE national average (ratio > 1.0) : {above_1:,} ({pct_above}%)")
print(f"Hospitals AT or BELOW national average          : {total_valid - above_1:,}")

# ── 6. Ratio by condition ─────────────────────────────────────────────────────
print("\n--- Average Excess Readmission Ratio by Condition ---")
ratio_by_condition = (
    df.groupby("measure_name")["excess_readmission_ratio"]
    .agg(["mean", "median", "count"])
    .round(4)
    .sort_values("mean", ascending=False)
)
ratio_by_condition.columns = ["avg_ratio", "median_ratio", "count"]
print(ratio_by_condition.to_string())

# ── 7. Top 10 worst hospitals ─────────────────────────────────────────────────
print("\n--- Top 10 Worst Hospitals (highest excess readmission ratio) ---")
top10_worst = (
    df[df["excess_readmission_ratio"].notna()]
    .nlargest(10, "excess_readmission_ratio")
    [["facility_name", "state", "measure_name", "excess_readmission_ratio"]]
    .reset_index(drop=True)
)
print(top10_worst.to_string())

# ── 8. Best hospitals ─────────────────────────────────────────────────────────
print("\n--- Top 10 Best Hospitals (lowest excess readmission ratio) ---")
top10_best = (
    df[df["excess_readmission_ratio"].notna()]
    .nsmallest(10, "excess_readmission_ratio")
    [["facility_name", "state", "measure_name", "excess_readmission_ratio"]]
    .reset_index(drop=True)
)
print(top10_best.to_string())

# ── 9. State analysis ─────────────────────────────────────────────────────────
print("\n--- Top 10 States by Average Excess Readmission Ratio ---")
state_avg = (
    df.groupby("state")["excess_readmission_ratio"]
    .mean()
    .round(4)
    .sort_values(ascending=False)
    .head(10)
)
print(state_avg.to_string())

# ── 10. Date range ────────────────────────────────────────────────────────────
print("\n--- Date Range ---")
if "start_date" in df.columns:
    print(f"Start dates: {df['start_date'].unique()[:5]}")
if "end_date" in df.columns:
    print(f"End dates  : {df['end_date'].unique()[:5]}")

# ── 11. Predicted vs Expected rates ──────────────────────────────────────────
print("\n--- Predicted vs Expected Readmission Rate ---")
df["predicted_readmission_rate"] = pd.to_numeric(
    df["predicted_readmission_rate"], errors="coerce"
)
df["expected_readmission_rate"] = pd.to_numeric(
    df["expected_readmission_rate"], errors="coerce"
)
print(df[["predicted_readmission_rate", "expected_readmission_rate"]].describe().round(3).to_string())

# ── 12. Risk tier preview ─────────────────────────────────────────────────────
print("\n--- Risk Tier Preview (what we will create in ETL) ---")
df["risk_tier"] = pd.cut(
    df["excess_readmission_ratio"],
    bins=[0, 1.0, 1.2, float("inf")],
    labels=["LOW", "MEDIUM", "HIGH"],
    right=True
)
risk_counts = df["risk_tier"].value_counts()
print(risk_counts.to_string())

# ── Save report ───────────────────────────────────────────────────────────────
os.makedirs("reports", exist_ok=True)
with open(REPORT_FILE, "w") as f:
    f.write("=" * 60 + "\n")
    f.write("EDA SUMMARY — Hospital Readmission Analytics\n")
    f.write("=" * 60 + "\n\n")
    f.write(f"Total rows       : {df.shape[0]:,}\n")
    f.write(f"Total columns    : {df.shape[1]}\n")
    f.write(f"Unique hospitals : {df['facility_name'].nunique():,}\n")
    f.write(f"Unique states    : {df['state'].nunique():,}\n")
    f.write(f"Unique conditions: {df['measure_name'].nunique():,}\n\n")
    f.write(f"Hospitals above national avg : {above_1:,} ({pct_above}%)\n\n")
    f.write("Conditions found:\n")
    for cond, cnt in condition_counts.items():
        f.write(f"  {cond}: {cnt:,} records\n")
    f.write("\nRisk tier distribution:\n")
    for tier, cnt in risk_counts.items():
        f.write(f"  {tier}: {cnt:,}\n")

print(f"\n--- EDA Complete ---")
print(f"Summary saved to: {REPORT_FILE}")
print("\nKey findings to note:")
print(f"  Total records   : {df.shape[0]:,}")
print(f"  Unique hospitals: {df['facility_name'].nunique():,}")
print(f"  Conditions found: {df['measure_name'].nunique()}")
print(f"  Above avg ratio : {pct_above}% of hospitals")

