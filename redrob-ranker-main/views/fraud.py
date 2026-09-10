import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


def render():
    st.title("🛡 Fraud Detection Dashboard")
    st.caption("AI-powered resume fraud detection from your ranked candidates")

    st.divider()

    # Get live data from session state
    result = st.session_state.get("ranking_result")

    if not result or not result.get("results"):
        st.warning("⚠ No ranking results available. Please upload a dataset on the **Upload Resumes** page first.")
        st.stop()

    results = result["results"]
    metadata = result.get("metadata", {})

    # Compute fraud metrics from live data
    total_input = metadata.get("total_input", len(results))
    honeypots_filtered = metadata.get("honeypots_filtered", 0)
    low_trust = [c for c in results if c["trust_score"] < 0.6]
    medium_trust = [c for c in results if 0.6 <= c["trust_score"] < 0.8]
    high_trust = [c for c in results if c["trust_score"] >= 0.8]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Scanned", total_input)
    c2.metric("Honeypots Filtered", honeypots_filtered)
    c3.metric("Low Trust", len(low_trust))
    c4.metric("Verified", len(high_trust))

    st.divider()

    left, right = st.columns([2, 1])

    with left:
        st.subheader("Trust Score Distribution")

        risk_df = pd.DataFrame({
            "Risk Level": ["High Trust (≥80%)", "Medium Trust (60-80%)", "Low Trust (<60%)"],
            "Candidates": [len(high_trust), len(medium_trust), len(low_trust)],
        })

        fig = px.bar(
            risk_df,
            x="Risk Level",
            y="Candidates",
            color="Candidates",
            template="plotly_dark",
            color_continuous_scale=["#00aa88", "#ff9f43", "#ff6b6b"],
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        # Trust score gauge
        avg_trust = sum(c["trust_score"] for c in results) / len(results) * 100

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=avg_trust,
            title={"text": "Avg Trust Score"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#00D4FF"},
                "steps": [
                    {"range": [0, 60], "color": "#ff6b6b"},
                    {"range": [60, 80], "color": "#ff9f43"},
                    {"range": [80, 100], "color": "#00aa88"},
                ],
            },
        ))
        fig.update_layout(template="plotly_dark", height=350)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Show suspicious candidates (low trust)
    st.subheader("⚠ Suspicious Candidates (Low Trust Score)")

    if low_trust:
        suspicious_df = pd.DataFrame({
            "Candidate ID": [c["candidate_id"] for c in low_trust],
            "Title": [c["title"] for c in low_trust],
            "Company": [c["company"] for c in low_trust],
            "Trust Score": [f"{c['trust_score']*100:.1f}%" for c in low_trust],
            "AI Score": [f"{c['score']*100:.1f}" for c in low_trust],
            "Reasoning": [c["reasoning"][:100] + "..." if len(c["reasoning"]) > 100 else c["reasoning"] for c in low_trust],
        })
        st.dataframe(suspicious_df, use_container_width=True, hide_index=True)
    elif honeypots_filtered > 0:
        st.info(f"All {honeypots_filtered} honeypot profiles were automatically filtered during ranking.")
    else:
        st.success("✅ No suspicious candidates detected. All profiles passed trust verification.")

    st.divider()

    # Show honeypot info
    if honeypots_filtered > 0:
        st.subheader("🚫 Honeypot Profiles Filtered")
        st.error(
            f"🚨 {honeypots_filtered} profiles were identified as impossible/fraudulent "
            f"and automatically removed from rankings."
        )
        st.markdown("""
        **Honeypot Detection Checks:**
        - Impossible career timelines
        - Skills count exceeding realistic limits
        - Contradictory employment dates
        - Profile completeness anomalies
        - Statistical outlier detection
        """)

    st.divider()

    # AI Recommendations
    st.subheader("AI Recommendation")

    if len(low_trust) == 0 and honeypots_filtered == 0:
        st.success("✔ All candidates appear verified and trustworthy")
    elif len(low_trust) > 0:
        st.warning(f"⚠ {len(low_trust)} candidates have low trust scores — review before proceeding")
    if honeypots_filtered > 0:
        st.error(f"🚨 {honeypots_filtered} fraudulent profiles were automatically blocked")
    st.info("📄 Trust scores are computed from career consistency, profile signals, and behavioral patterns")
