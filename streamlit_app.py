"""
streamlit_app.py
Hospital Readmission Risk Analytics — Interactive Dashboard
Features: Hospital search, KPI cards, AI-generated insights,
          condition breakdown, state filtering
"""

import os
import streamlit as st
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

st.set_page_config(
    page_title="Hospital Readmission Risk Analytics",
    page_icon="🏥",
    layout="wide"
)

# ─────────────────────────────────────────────────────────────
# DATABASE CONNECTION
# ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_engine():
    return create_engine(DB_URL)

@st.cache_data(ttl=300)
def load_kpi_data():
    engine = get_engine()
    query = text("SELECT * FROM v_hospital_recommendations")
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

@st.cache_data(ttl=300)
def load_national_summary():
    engine = get_engine()
    query = text("SELECT * FROM v_national_summary")
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

@st.cache_data(ttl=300)
def load_state_scorecard():
    engine = get_engine()
    query = text("SELECT * FROM v_state_scorecard")
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

# ─────────────────────────────────────────────────────────────
# AI INSIGHT GENERATOR
# ─────────────────────────────────────────────────────────────
def generate_ai_insight(hospital_data):
    """Generate AI insight for a single hospital using Groq."""
    if not GROQ_API_KEY:
        return "Groq API key not configured.", "Please add GROQ_API_KEY to .env file."

    client = Groq(api_key=GROQ_API_KEY)

    prompt = f"""Given the following hospital performance data:

- Facility ID: {hospital_data['facility_id']}
- State: {hospital_data['state']}
- Condition: {hospital_data['condition_name']}
- Risk Tier: {hospital_data['risk_tier']}
- Excess Readmission Ratio: {hospital_data['excess_readmission_ratio']:.4f} (1.0 = national average)
- Readmission Rate vs National Avg: {hospital_data['readmission_rate']:.2f}%
- Estimated Penalty Cost: ${hospital_data['penalty_cost']:,.0f}
- Risk Score: {hospital_data['risk_score']:.1f}/100
- Rank in State: #{hospital_data['hospital_rank_in_state']}

Provide:
1. A 2-sentence insight about this hospital's readmission performance vs. the national average.
2. One specific, actionable clinical recommendation for their leadership team.

Format your response exactly as:
Insight: [your 2-sentence insight]
Recommendation: [your specific recommendation]"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are a healthcare analytics consultant. Provide data-driven insights and actionable clinical recommendations. Be specific, reference the numbers, and focus on patient outcomes."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )

        result = response.choices[0].message.content.strip()

        if "Insight:" in result and "Recommendation:" in result:
            parts = result.split("Recommendation:")
            insight = parts[0].replace("Insight:", "").strip()
            recommendation = parts[1].strip()
            return insight, recommendation
        else:
            return result, hospital_data['recommended_action']

    except Exception as e:
        return f"Error: {e}", hospital_data['recommended_action']


# ─────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────
try:
    df = load_kpi_data()
    df_national = load_national_summary()
    df_states = load_state_scorecard()
    data_loaded = True
except Exception as e:
    st.error(f"Database connection error: {e}")
    data_loaded = False

if not data_loaded:
    st.stop()

# ─────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────
st.title("🏥 Hospital Readmission Risk Analytics")
st.markdown("**CMS Hospital Readmissions Reduction Program** — Tracking penalty exposure, risk scores, and AI-generated clinical recommendations across 3,000+ U.S. hospitals.")
st.markdown("---")

# ─────────────────────────────────────────────────────────────
# SIDEBAR FILTERS
# ─────────────────────────────────────────────────────────────
st.sidebar.header("Filters")

# State filter
states = sorted(df['state'].unique().tolist())
selected_state = st.sidebar.selectbox(
    "Select State",
    options=["All States"] + states
)

# Condition filter
conditions = sorted(df['condition_name'].unique().tolist())
selected_condition = st.sidebar.selectbox(
    "Select Condition",
    options=["All Conditions"] + conditions
)

# Risk tier filter
risk_tiers = ["All Tiers", "HIGH", "MEDIUM", "LOW"]
selected_tier = st.sidebar.selectbox("Select Risk Tier", risk_tiers)

# Apply filters
df_filtered = df.copy()
if selected_state != "All States":
    df_filtered = df_filtered[df_filtered['state'] == selected_state]
if selected_condition != "All Conditions":
    df_filtered = df_filtered[df_filtered['condition_name'] == selected_condition]
if selected_tier != "All Tiers":
    df_filtered = df_filtered[df_filtered['risk_tier'] == selected_tier]

# ─────────────────────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────────────────────
st.subheader("Key Performance Indicators")

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_penalty = df_filtered['penalty_cost'].sum()
    st.metric(
        label="Total Penalty Exposure",
        value=f"${total_penalty:,.0f}"
    )

with col2:
    avg_risk = df_filtered['risk_score'].mean()
    st.metric(
        label="Avg Risk Score",
        value=f"{avg_risk:.1f}/100"
    )

with col3:
    avg_readmission = df_filtered['readmission_rate'].mean()
    st.metric(
        label="Avg Readmission Rate",
        value=f"{avg_readmission:.1f}%"
    )

with col4:
    hospital_count = df_filtered['facility_id'].nunique()
    st.metric(
        label="Hospitals",
        value=f"{hospital_count:,}"
    )

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# CONDITION BREAKDOWN
# ─────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Condition Breakdown")
    condition_stats = df_filtered.groupby('condition_name').agg(
        avg_ratio=('excess_readmission_ratio', 'mean'),
        total_penalty=('penalty_cost', 'sum'),
        hospital_count=('facility_id', 'nunique')
    ).round(4).sort_values('avg_ratio', ascending=False)

    st.bar_chart(condition_stats['avg_ratio'])

with col_right:
    st.subheader("Risk Tier Distribution")
    tier_counts = df_filtered['risk_tier'].value_counts()
    st.bar_chart(tier_counts)

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# HIGH RISK HOSPITALS TABLE
# ─────────────────────────────────────────────────────────────
st.subheader("High Risk Hospitals")

high_risk = df_filtered[df_filtered['risk_tier'] == 'HIGH'].sort_values(
    'risk_score', ascending=False
).head(20)

if len(high_risk) > 0:
    display_cols = [
        'facility_id', 'state', 'condition_name', 'risk_tier',
        'risk_score', 'penalty_cost', 'readmission_rate',
        'recommended_action'
    ]
    st.dataframe(
        high_risk[display_cols].reset_index(drop=True),
        use_container_width=True,
        height=400
    )
else:
    st.info("No HIGH risk hospitals match your current filters.")

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# AI INSIGHT GENERATOR
# ─────────────────────────────────────────────────────────────
st.subheader("🤖 AI-Powered Hospital Insight Generator")
st.markdown("Select a hospital to generate an AI-powered clinical insight and recommendation.")

# Hospital search
facility_ids = sorted(df_filtered['facility_id'].unique().tolist())

selected_facility = st.selectbox(
    "Search Hospital by Facility ID",
    options=facility_ids,
    index=0 if len(facility_ids) > 0 else None
)

if selected_facility:
    hospital_rows = df_filtered[df_filtered['facility_id'] == selected_facility]

    if len(hospital_rows) > 0:
        # Show hospital profile
        st.markdown("#### Hospital Profile")

        for _, row in hospital_rows.iterrows():
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Condition", row['condition_name'])
                st.metric("Risk Tier", row['risk_tier'])
            with col_b:
                st.metric("Risk Score", f"{row['risk_score']:.1f}/100")
                st.metric("Penalty Cost", f"${row['penalty_cost']:,.0f}")
            with col_c:
                st.metric("Readmission Rate", f"{row['readmission_rate']:.1f}%")
                st.metric("State Rank", f"#{row['hospital_rank_in_state']}")

            # Show SQL recommendation
            st.info(f"**SQL Recommendation:** {row['recommended_action']}")

            # AI Insight button
            if st.button(f"Generate AI Insight for {row['condition_name']}", key=f"ai_{row['facility_id']}_{row['condition_name']}"):
                with st.spinner("Generating AI insight..."):
                    insight, recommendation = generate_ai_insight(row)

                st.success(f"**AI Insight:** {insight}")
                st.warning(f"**AI Recommendation:** {recommendation}")

            st.markdown("---")

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 14px;'>
        <p>Hospital Readmission Risk Analytics | Built by Rajasekhar Reddy Byreddy</p>
        <p>Data: CMS Hospital Readmissions Reduction Program (FY2026) | AI: Groq LLM</p>
        <p>Stack: Python · PostgreSQL · Streamlit · Groq API · Tableau · Power BI</p>
    </div>
    """,
    unsafe_allow_html=True
)
