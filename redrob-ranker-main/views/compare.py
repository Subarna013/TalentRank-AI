import streamlit as st
import plotly.graph_objects as go
from utils.api_client import compare_candidates


def render():
    st.title("⚖ AI Candidate Comparison")
    st.caption("Compare candidates side-by-side using backend AI analysis")

    st.divider()

    # Get live data from session state
    result = st.session_state.get("ranking_result")
    candidates_raw = st.session_state.get("uploaded_candidates")

    if not result or not result.get("results") or not candidates_raw:
        st.warning("⚠ No ranking results available. Please upload a dataset on the **Upload Resumes** page first.")
        st.stop()

    results = result["results"]

    # Build candidate lookup: candidate_id -> raw data
    candidate_lookup = {}
    for raw in candidates_raw:
        cid = raw.get("candidate_id", "")
        candidate_lookup[cid] = raw

    # Build display options
    options = []
    for c in results[:20]:  # Top 20 candidates for comparison
        label = f"{c['candidate_id']} — {c['title']} @ {c['company']} (Score: {c['score']*100:.1f})"
        options.append((label, c["candidate_id"]))

    if len(options) < 2:
        st.warning("Need at least 2 ranked candidates for comparison.")
        st.stop()

    # Selection
    left, right = st.columns(2)

    with left:
        sel_a = st.selectbox(
            "Candidate A",
            range(len(options)),
            format_func=lambda i: options[i][0],
            index=0,
        )

    with right:
        default_b = min(1, len(options) - 1)
        sel_b = st.selectbox(
            "Candidate B",
            range(len(options)),
            format_func=lambda i: options[i][0],
            index=default_b,
        )

    cid_a = options[sel_a][1]
    cid_b = options[sel_b][1]

    if cid_a == cid_b:
        st.warning("Please select two different candidates to compare.")
        st.stop()

    # Get the raw candidate data for comparison API call
    raw_a = candidate_lookup.get(cid_a)
    raw_b = candidate_lookup.get(cid_b)

    if not raw_a or not raw_b:
        st.error("Could not find raw candidate data for selected candidates.")
        st.stop()

    # Call backend compare endpoint
    st.divider()

    try:
        with st.spinner("🤖 Comparing candidates..."):
            comparison = compare_candidates({"candidates": [raw_a, raw_b]})
    except Exception as e:
        st.error(f"❌ Comparison failed: {e}")
        st.stop()

    candidates_compared = comparison.get("candidates", [])

    if len(candidates_compared) < 2:
        st.error("Backend returned insufficient comparison data.")
        st.stop()

    # Find A and B in the response
    comp_a = next((c for c in candidates_compared if c["candidate_id"] == cid_a), candidates_compared[0])
    comp_b = next((c for c in candidates_compared if c["candidate_id"] == cid_b), candidates_compared[1])

    # Display metrics side by side
    a_col, b_col = st.columns(2)

    with a_col:
        st.subheader(f"🅰️ {comp_a['candidate_id']}")
        st.caption(f"{comp_a['title']} @ {comp_a['company']}")
        st.metric("AI Score", f"{comp_a['score']*100:.1f}")
        st.metric("Trust", f"{comp_a['trust']*100:.1f}%")
        st.metric("Experience", f"{comp_a['years']} yrs")
        st.metric("Technical Fit", f"{comp_a['technical_fit']*100:.1f}%")
        st.metric("Mutual Interest", f"{comp_a['mutual_interest']*100:.1f}%")
        if comp_a["is_honeypot"]:
            st.error("⚠ Flagged as honeypot")

    with b_col:
        st.subheader(f"🅱️ {comp_b['candidate_id']}")
        st.caption(f"{comp_b['title']} @ {comp_b['company']}")
        st.metric("AI Score", f"{comp_b['score']*100:.1f}")
        st.metric("Trust", f"{comp_b['trust']*100:.1f}%")
        st.metric("Experience", f"{comp_b['years']} yrs")
        st.metric("Technical Fit", f"{comp_b['technical_fit']*100:.1f}%")
        st.metric("Mutual Interest", f"{comp_b['mutual_interest']*100:.1f}%")
        if comp_b["is_honeypot"]:
            st.error("⚠ Flagged as honeypot")

    st.divider()

    # Radar chart comparison
    st.subheader("📊 Multi-Dimensional Comparison")

    categories = ["Overall Score", "Technical Fit", "Career Evidence", "Mutual Interest", "Trust"]

    values_a = [
        comp_a["score"] * 100,
        comp_a["technical_fit"] * 100,
        comp_a["career_evidence"] * 100,
        comp_a["mutual_interest"] * 100,
        comp_a["trust"] * 100,
    ]

    values_b = [
        comp_b["score"] * 100,
        comp_b["technical_fit"] * 100,
        comp_b["career_evidence"] * 100,
        comp_b["mutual_interest"] * 100,
        comp_b["trust"] * 100,
    ]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values_a,
        theta=categories,
        fill="toself",
        name=comp_a["candidate_id"],
    ))

    fig.add_trace(go.Scatterpolar(
        r=values_b,
        theta=categories,
        fill="toself",
        name=comp_b["candidate_id"],
    ))

    fig.update_layout(
        template="plotly_dark",
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # AI Recommendation
    st.subheader("🏆 AI Recommendation")

    if comp_a["score"] > comp_b["score"]:
        winner = comp_a
        loser = comp_b
        diff = (comp_a["score"] - comp_b["score"]) * 100
        st.success(
            f"**{winner['candidate_id']}** is ranked higher by {diff:.1f} points. "
            f"Stronger in overall scoring with {winner['years']} years experience at {winner['company']}."
        )
    else:
        winner = comp_b
        loser = comp_a
        diff = (comp_b["score"] - comp_a["score"]) * 100
        st.success(
            f"**{winner['candidate_id']}** is ranked higher by {diff:.1f} points. "
            f"Stronger in overall scoring with {winner['years']} years experience at {winner['company']}."
        )
