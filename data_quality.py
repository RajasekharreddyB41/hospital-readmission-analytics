"""
data_quality.py
===============
Step 3 — Data Quality Checks
Validate before you clean — this is the senior analyst habit.
Run this BEFORE the ETL pipeline.

Usage:
    python data_quality.py
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
RAW_FILE    = os.path.join("data", "raw", "readmissions_raw.csv")
REPORT_FILE = os.path.join("reports", "data_quality_report.txt")

# Valid US state codes (50 states + DC)
VALID_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA",
    "HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
    "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
    "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"
}

# Expected CMS conditions
EXPECTED_CONDITIONS = {
    "READM-30-HF-HRRP",
    "READM-30-PN-HRRP",
    "READM-30-COPD-HRRP",
    "READM-30-HIP-KNEE-HRRP",
    "READM-30-CABG-HRRP",
    "READM-30-AMI-HRRP"
}

report_lines = []

def log(msg=""):
    print(msg)
    report_lines.append(msg)

def section(title):
    line = "\n" + "=" * 60
    log(line)
    log(f"  {title}")
    log("=" * 60)

# ── Load data ─────────────────────────────────────────────────────────────────
section("Hospital Readmission Analytics — Data Quality Report")
log(f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log(f"Source    : {RAW_FILE}")

df = pd.read_csv(RAW_FILE, encoding="utf-8-sig")
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

log(f"\nTotal rows loaded : {len(df):,}")
log(f"Total columns     : {df.shape[1]}")

total_issues = 0

# ── CHECK 1: Missing values ───────────────────────────────────────────────────
section("CHECK 1 — Missing Values")

missing = df.isnull().sum()
missing_pct = (missing / len(df) * 100).round(2)

flagged_cols = []
for col in df.columns:
    pct = missing_pct[col]
    count = missing[col]
    status = "FAIL" if pct > 5 else "PASS"
    flag   = " <-- FLAG" if pct > 5 else ""
    log(f"  {col:<35} {count:>6} missing  ({pct:>6.2f}%)  [{status}]{flag}")
    if pct > 5:
        flagged_cols.append(col)
        total_issues += count

log(f"\nColumns with > 5% missing : {len(flagged_cols)}")
for c in flagged_cols:
    log(f"  - {c} ({missing_pct[c]:.1f}% missing)")

log("\nNOTE: excess_readmission_ratio missing 36% — these are hospitals")
log("      with too few cases to calculate a reliable ratio (CMS policy).")
log("      These rows will be dropped in the ETL step.")

# ── CHECK 2: Duplicate records ────────────────────────────────────────────────
section("CHECK 2 — Duplicate Records")

# A duplicate = same hospital + same condition
dups = df.duplicated(subset=["facility_id", "measure_name"], keep=False)
dup_count = dups.sum()

if dup_count == 0:
    log("  PASS — No duplicate hospital + condition combinations found.")
else:
    log(f"  FAIL — {dup_count:,} duplicate rows found!")
    log("\n  Sample duplicates:")
    sample = df[dups][["facility_name", "state", "measure_name"]].head(5)
    log(sample.to_string(index=False))
    total_issues += dup_count

# ── CHECK 3: Invalid state codes ─────────────────────────────────────────────
section("CHECK 3 — Invalid State Codes")

invalid_states = df[~df["state"].isin(VALID_STATES)]
invalid_count  = len(invalid_states)

if invalid_count == 0:
    log("  PASS — All state codes are valid US states.")
else:
    log(f"  FAIL — {invalid_count:,} rows with invalid state codes:")
    bad_states = invalid_states["state"].value_counts()
    log(bad_states.to_string())
    total_issues += invalid_count

log(f"\n  Valid states found in dataset: {sorted(df['state'].unique())}")

# ── CHECK 4: Ratio range validation ──────────────────────────────────────────
section("CHECK 4 — Excess Readmission Ratio Range (valid: 0.0 to 5.0)")

df["excess_readmission_ratio"] = pd.to_numeric(
    df["excess_readmission_ratio"], errors="coerce"
)

ratio_valid = df["excess_readmission_ratio"].dropna()
out_of_range = df[
    (df["excess_readmission_ratio"] < 0) |
    (df["excess_readmission_ratio"] > 5)
]

log(f"  Valid ratio rows   : {len(ratio_valid):,}")
log(f"  Out-of-range rows  : {len(out_of_range):,}")
log(f"  Min ratio found    : {ratio_valid.min():.4f}")
log(f"  Max ratio found    : {ratio_valid.max():.4f}")

if len(out_of_range) == 0:
    log("  PASS — All ratio values are within expected range (0–5).")
else:
    log(f"  FAIL — {len(out_of_range)} rows outside valid range!")
    log(out_of_range[["facility_name", "state", "excess_readmission_ratio"]].to_string())
    total_issues += len(out_of_range)

# ── CHECK 5: Conditions validation ───────────────────────────────────────────
section("CHECK 5 — CMS Condition Codes")

found_conditions    = set(df["measure_name"].unique())
unexpected_conds    = found_conditions - EXPECTED_CONDITIONS
missing_conds       = EXPECTED_CONDITIONS - found_conditions

log(f"  Expected conditions : {len(EXPECTED_CONDITIONS)}")
log(f"  Found conditions    : {len(found_conditions)}")

if not unexpected_conds and not missing_conds:
    log("  PASS — All conditions match expected CMS codes.")
    for c in sorted(found_conditions):
        cnt = len(df[df["measure_name"] == c])
        log(f"    {c} : {cnt:,} records")
else:
    if unexpected_conds:
        log(f"  WARNING — Unexpected conditions: {unexpected_conds}")
        total_issues += len(unexpected_conds)
    if missing_conds:
        log(f"  WARNING — Missing expected conditions: {missing_conds}")

# ── CHECK 6: Facility ID format ───────────────────────────────────────────────
section("CHECK 6 — Facility ID Format")

df["facility_id"] = pd.to_numeric(df["facility_id"], errors="coerce")
bad_ids = df[df["facility_id"].isna()]

if len(bad_ids) == 0:
    log(f"  PASS — All {df['facility_id'].nunique():,} facility IDs are numeric.")
    log(f"  ID range: {int(df['facility_id'].min())} to {int(df['facility_id'].max())}")
else:
    log(f"  FAIL — {len(bad_ids)} rows with non-numeric facility IDs")
    total_issues += len(bad_ids)

# ── CHECK 7: Discharge counts ─────────────────────────────────────────────────
section("CHECK 7 — Number of Discharges (sanity check)")

df["number_of_discharges"] = pd.to_numeric(
    df["number_of_discharges"], errors="coerce"
)
discharges_valid = df["number_of_discharges"].dropna()
negative_discharges = df[df["number_of_discharges"] < 0]

log(f"  Valid discharge rows : {len(discharges_valid):,}")
log(f"  Negative values      : {len(negative_discharges):,}")
if len(discharges_valid) > 0:
    log(f"  Min discharges       : {discharges_valid.min():.0f}")
    log(f"  Max discharges       : {discharges_valid.max():.0f}")
    log(f"  Avg discharges       : {discharges_valid.mean():.0f}")

if len(negative_discharges) == 0:
    log("  PASS — No negative discharge counts found.")
else:
    log(f"  FAIL — {len(negative_discharges)} rows with negative discharges!")
    total_issues += len(negative_discharges)

# ── SUMMARY ───────────────────────────────────────────────────────────────────
section("DATA QUALITY SUMMARY")

log(f"  Total rows checked    : {len(df):,}")
log(f"  Total issues flagged  : {total_issues:,}")
log(f"  Duplicate rows        : {dup_count:,}")
log(f"  Invalid states        : {invalid_count:,}")
log(f"  Out-of-range ratios   : {len(out_of_range):,}")
log(f"  Missing ratio rows    : {df['excess_readmission_ratio'].isna().sum():,}")
log(f"\n  VERDICT: {'CLEAN ENOUGH TO PROCEED' if total_issues < 100 else 'NEEDS CLEANING'}")
log(f"\n  ACTION: ETL pipeline will drop rows where ratio is null.")
log(f"          These represent hospitals below CMS minimum case threshold.")
log(f"          Remaining rows after drop: ~{df['excess_readmission_ratio'].notna().sum():,}")

# ── Resume bullet ──────────────────────────────────────────────────────────────
log("\n" + "-" * 60)
log("  RESUME BULLET (copy this):")
log("-" * 60)
log(f"  'Implemented automated data quality validation across")
log(f"   {len(df):,} CMS hospital records — flagging {total_issues:,} issues")
log(f"   across 7 checks including missing values, duplicates,")
log(f"   invalid state codes, and out-of-range ratio values.'")

# ── Save report ────────────────────────────────────────────────────────────────
os.makedirs("reports", exist_ok=True)
with open(REPORT_FILE, "w") as f:
    f.write("\n".join(report_lines))

log(f"\nReport saved to: {REPORT_FILE}")

