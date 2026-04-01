"""
ai_insights.py
Hospital Readmission Analytics — AI Insight Generator
Queries top 50 high-risk hospitals from PostgreSQL
Generates Insight + Recommendation using Groq LLM
Saves output to reports/ai_hospital_insights.csv
"""

import os
import time
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from groq import Groq

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

OUTPUT_FILE = os.path.join("reports", "ai_hospital_insights.csv")
EXAMPLES_FILE = os.path.join("reports", "ai_output_examples.txt")
MODEL = "llama-3.1-8b-instant"
TOP_N = 50

def log(msg):
    print(msg)


# ─────────────────────────────────────────────────────────────
# STEP 1: Query top 50 high-risk hospitals
# ─────────────────────────────────────────────────────────────
log("=" * 60)
log("  AI INSIGHT GENERATOR")
log("=" * 60)

if not DB_URL:
    log("ERROR: DATABASE_URL not set in .env")
    exit(1)

if not GROQ_API_KEY:
    log("ERROR: GROQ_API_KEY not set in .env")
    exit(1)

log("\nStep 1: Querying top 50 high-risk hospitals...")

engine = create_engine(DB_URL)

query = text("""
    SELECT
        r.facility_id,
        r.state,
        r.condition_name,
        r.risk_tier,
        r.recommended_action,
        ROUND(r.excess_readmission_ratio::numeric, 4) AS excess_ratio,
        ROUND(r.penalty_cost::numeric, 0)              AS penalty_cost,
        ROUND(r.risk_score::numeric, 1)                AS risk_score,
        ROUND(r.readmission_rate::numeric, 2)          AS readmission_rate,
        ROUND(r.improvement_rate::numeric, 2)          AS improvement_rate,
        r.hospital_rank_in_state
    FROM v_hospital_recommendations r
    WHERE r.risk_tier = 'HIGH'
    ORDER BY r.risk_score DESC
    LIMIT :limit
""")

with engine.connect() as conn:
    df = pd.read_sql(query, conn, params={"limit": TOP_N})

log(f"  Retrieved {len(df)} high-risk hospitals")
log(f"  States: {df['state'].nunique()} unique")
log(f"  Conditions: {df['condition_name'].unique().tolist()}")


# ─────────────────────────────────────────────────────────────
# STEP 2: Generate AI insights using Groq
# ─────────────────────────────────────────────────────────────
log("\nStep 2: Generating AI insights with Groq...")
log(f"  Model: {MODEL}")
log(f"  Processing {len(df)} hospitals...\n")

client = Groq(api_key=GROQ_API_KEY)

insights = []
recommendations = []
errors = 0

for idx, row in df.iterrows():
    hospital_num = idx + 1

    # Build the consulting-level prompt
    prompt = f"""Given the following hospital performance data:

- Facility ID: {row['facility_id']}
- State: {row['state']}
- Condition: {row['condition_name']}
- Risk Tier: {row['risk_tier']}
- Excess Readmission Ratio: {row['excess_ratio']} (1.0 = national average)
- Readmission Rate vs National Avg: {row['readmission_rate']}%
- Estimated Penalty Cost: ${row['penalty_cost']:,.0f}
- Risk Score: {row['risk_score']}/100
- Improvement Rate: {row['improvement_rate']}%
- Rank in State: #{row['hospital_rank_in_state']}

Provide:
1. A 2-sentence insight about this hospital's readmission performance vs. the national average.
2. One specific, actionable clinical recommendation for their leadership team.

Format your response exactly as:
Insight: [your 2-sentence insight]
Recommendation: [your specific recommendation]"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a healthcare analytics consultant. Provide data-driven insights and actionable clinical recommendations. Be specific, reference the numbers, and focus on patient outcomes."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=300
        )

        result = response.choices[0].message.content.strip()

        # Parse Insight and Recommendation
        insight = ""
        recommendation = ""

        if "Insight:" in result and "Recommendation:" in result:
            parts = result.split("Recommendation:")
            insight = parts[0].replace("Insight:", "").strip()
            recommendation = parts[1].strip()
        else:
            insight = result
            recommendation = row['recommended_action']

        insights.append(insight)
        recommendations.append(recommendation)

        log(f"  [{hospital_num}/{len(df)}] Facility {row['facility_id']} ({row['state']}) — {row['condition_name']} ✓")

        # Rate limiting — Groq free tier allows 30 requests/min
        time.sleep(2.5)

    except Exception as e:
        log(f"  [{hospital_num}/{len(df)}] Facility {row['facility_id']} — ERROR: {e}")
        insights.append("Error generating insight")
        recommendations.append(row['recommended_action'])
        errors += 1
        time.sleep(5)

# ─────────────────────────────────────────────────────────────
# STEP 3: Save results
# ─────────────────────────────────────────────────────────────
log(f"\nStep 3: Saving results...")

df['ai_insight'] = insights
df['ai_recommendation'] = recommendations

# Create reports folder if needed
os.makedirs("reports", exist_ok=True)

# Save full CSV
df.to_csv(OUTPUT_FILE, index=False)
log(f"  Saved {len(df)} rows to {OUTPUT_FILE}")

# Save 3 example outputs for GitHub
with open(EXAMPLES_FILE, "w", encoding="utf-8") as f:
    f.write("=" * 70 + "\n")
    f.write("AI-GENERATED HOSPITAL INSIGHTS — SAMPLE OUTPUT\n")
    f.write("Model: Groq llama-3.1-8b-instant\n")
    f.write("=" * 70 + "\n\n")

    for i in range(min(3, len(df))):
        row = df.iloc[i]
        f.write(f"--- Hospital {i+1} ---\n")
        f.write(f"Facility ID : {row['facility_id']}\n")
        f.write(f"State       : {row['state']}\n")
        f.write(f"Condition   : {row['condition_name']}\n")
        f.write(f"Risk Score  : {row['risk_score']}/100\n")
        f.write(f"Penalty Cost: ${row['penalty_cost']:,.0f}\n")
        f.write(f"Excess Ratio: {row['excess_ratio']}\n\n")
        f.write(f"AI Insight:\n{row['ai_insight']}\n\n")
        f.write(f"AI Recommendation:\n{row['ai_recommendation']}\n\n")
        f.write("-" * 70 + "\n\n")

log(f"  Saved 3 examples to {EXAMPLES_FILE}")

# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────
log("\n" + "=" * 60)
log("  AI INSIGHT GENERATION COMPLETE")
log("=" * 60)
log(f"  Hospitals processed : {len(df)}")
log(f"  Successful          : {len(df) - errors}")
log(f"  Errors              : {errors}")
log(f"  Output CSV          : {OUTPUT_FILE}")
log(f"  Example file        : {EXAMPLES_FILE}")
log(f"\nReady for Step 9 — Streamlit App")
