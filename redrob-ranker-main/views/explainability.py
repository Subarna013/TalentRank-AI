import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils.api_client import explain_candidate


def render():
    st.title("🤖 AI Explainability")
    st.caption("Understand why the AI ranked each candidate.")

    st.divider()

    # Get live data from session state
    result = st.session_state.get("ranking_result")
    candidates_raw = st.session_state.get("uploaded_candidates")

    if not result or not result.get("results") or not candidates_raw:
        st.warning("⚠ No ranking results available. Please upload a dataset on the **Upload Resumes** page first.")
        st.stop()

    results = result["results"]

    # Build candidate lookup
    candidate_lookup = {}
    for raw in candidates_raw:
        cid = raw.get("candidate_id", "")
        candidate_lookup[cid] = raw

    # Build selectable options
    options = []
    for c in results[:30]:
        label = f"#{c['rank']} — {c['candidate_id']} | {c['title']} @ {c['company']} (Score: {c['score']*100:.1f})"
        options.append((label, c["candidate_id"]))

    st.subheader("👤 Select Candidate")

    selected_idx = st.selectbox(
        "Choose a candidate to explain",
        range(len(options)),
        format_func=lambda i: options[i][0],
    )

    selected_cid = options[selected_idx][1]
    raw_candidate = candidate_lookup.get(selected_cid)

    if not raw_candidate:
        st.error(f"Could not find raw data for {selected_cid}")
        st.stop()

    # Call backend explain endpoint
    st.divider()

    try:
        with st.spinner("🧠 Generating explanation..."):
            explanation = explain_candidate({"candidate": raw_candidate})
    except Exception as e:
        st.error(f"❌ Explanation failed: {e}")
        st.stop()

    # Display results
    overall_score = explanation["overall_score"] * 100

    left, right = st.columns([1, 1])

    with left:
        st.metric("Final AI Score", f"{overall_score:.1f}")

        # Determine decision
        if overall_score >= 85:
            st.metric("Hiring Decision", "HIRE")
        elif overall_score >= 70:
            st.metric("Hiring Decision", "REVIEW")
        else:
            st.metric("Hiring Decision", "REJECT")

        trust = explanation["honeypot_analysis"]["trust"] * 100
        st.metric("Trust Score", f"{trust:.1f}%")

    with right:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=overall_score,
            title={"text": "AI Score"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#00D4FF"},
                "steps": [
                    {"range": [0, 50], "color": "#3b3b3b"},
                    {"range": [50, 75], "color": "#555"},
                    {"range": [75, 100], "color": "#00aa88"},
                ],
            },
        ))
        fig.update_layout(template="plotly_dark", height=300)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Feature Breakdown
    st.subheader("📊 Score Contribution by Category")

    fb = explanation["feature_breakdown"]

    # Aggregate category scores
    categories = {
        "Skills": (
            fb["skills"]["semantic_score"]
            + fb["skills"]["proficiency_score"]
            + fb["skills"]["depth_score"]
        ) / 3 * 100,
        "Career": (
            fb["career"]["title_relevance"]
            + fb["career"]["trajectory"]
            + fb["career"]["stability"]
        ) / 3 * 100,
        "Experience": fb["experience"]["fit_score"] * 100,
        "Behavioral": (
            fb["behavioral"]["engagement"]
            + fb["behavioral"]["availability"]
            + fb["behavioral"]["platform_trust"]
        ) / 3 * 100,
        "Mutual Interest": explanation["mutual_interest"].get("mutual_interest_score", 0) * 100,
    }

    score_df = pd.DataFrame({
        "Feature": list(categories.keys()),
        "Contribution": [round(v, 1) for v in categories.values()],
    })

    st.bar_chart(score_df.set_index("Feature"))

    st.divider()

    # Detailed Feature Breakdown
    st.subheader("🔍 Detailed Feature Breakdown")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Skills**")
        st.write(f"- Semantic Match: {fb['skills']['semantic_score']:.3f}")
        st.write(f"- Proficiency: {fb['skills']['proficiency_score']:.3f}")
        st.write(f"- Depth: {fb['skills']['depth_score']:.3f}")
        st.write(f"- Endorsements: {fb['skills']['endorsement_score']:.3f}")
        st.write(f"- Anti-Skill Penalty: {fb['skills']['anti_skill_penalty']:.3f}")
        st.write(f"- Required Skills Matched: {fb['skills']['required_count']}")
        st.write(f"- Preferred Skills Matched: {fb['skills']['preferred_count']}")

        st.markdown("**Experience**")
        st.write(f"- Fit Score: {fb['experience']['fit_score']:.3f}")
        st.write(f"- Years: {fb['experience']['years']}")
        st.write(f"- In Range: {'✅' if fb['experience']['in_range'] else '❌'}")
        st.write(f"- Domain Months: {fb['experience']['domain_months']}")

    with col2:
        st.markdown("**Career**")
        st.write(f"- Title Relevance: {fb['career']['title_relevance']:.3f}")
        st.write(f"- Trajectory: {fb['career']['trajectory']:.3f}")
        st.write(f"- Product Company Ratio: {fb['career']['product_company_ratio']:.3f}")
        st.write(f"- Consulting Only: {'⚠️' if fb['career']['consulting_only'] else '✅'}")
        st.write(f"- Stability: {fb['career']['stability']:.3f}")
        st.write(f"- Recency: {fb['career']['recency']:.3f}")
        st.write(f"- Consistency: {fb['career']['consistency']:.3f}")

        st.markdown("**Behavioral**")
        st.write(f"- Engagement: {fb['behavioral']['engagement']:.3f}")
        st.write(f"- Availability: {fb['behavioral']['availability']:.3f}")
        st.write(f"- Platform Trust: {fb['behavioral']['platform_trust']:.3f}")
        st.write(f"- Recruiter Interest: {fb['behavioral']['recruiter_interest']:.3f}")

    st.divider()

    # Canonical Skills Coverage
    st.subheader("🎯 Canonical Skills Coverage")

    canonical = explanation.get("canonical_skills", {})
    if canonical:
        can_col1, can_col2 = st.columns(2)
        with can_col1:
            core_coverage = canonical.get("canonical_core_coverage", 0) * 100
            st.metric("Core Coverage", f"{core_coverage:.1f}%")
        with can_col2:
            categories_covered = canonical.get("categories_covered", 0)
            st.metric("Categories Covered", categories_covered)

        matched = canonical.get("matched_categories", [])
        if matched:
            st.success(f"Matched: {', '.join(matched[:10])}")

    st.divider()

    # Honeypot Analysis
    st.subheader("🛡 Trust Analysis")

    honeypot = explanation["honeypot_analysis"]
    if honeypot["is_honeypot"]:
        st.error("🚨 This profile was flagged as a honeypot!")
        for reason in honeypot.get("reasons", []):
            st.warning(f"⚠ {reason}")
    else:
        st.success(f"✅ Profile verified — Trust Score: {trust:.1f}%")

    st.divider()

    # AI Reasoning
    st.subheader("🧠 AI Reasoning")

    st.info(explanation["reasoning"])

    st.divider()

    # Mutual Interest
    mi = explanation.get("mutual_interest", {})
    if mi:
        st.subheader("🤝 Mutual Interest Score")
        mi_score = mi.get("mutual_interest_score", 0) * 100
        st.metric("Mutual Interest", f"{mi_score:.1f}%")
        st.caption("Combines response probability, candidate interest signals, and hireability.")
