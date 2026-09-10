import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np


def render():
    st.title("📊 Recruitment Analytics")
    st.markdown("AI-powered hiring insights from your uploaded dataset.")

    st.divider()

    # Get live data from session state
    result = st.session_state.get("ranking_result")
    candidates_raw = st.session_state.get("uploaded_candidates")

    if not result or not result.get("results"):
        st.warning("⚠ No ranking results available. Please upload a dataset on the **Upload Resumes** page first.")
        st.stop()

    results = result["results"]
    metadata = result.get("metadata", {})
    thresholds = st.session_state.get("thresholds", {"hire": 85, "review": 70})

    # =========================
    # KPI - LIVE DATA
    # =========================

    total = metadata.get("total_input", len(results))
    hire_count = sum(1 for c in results if c["score"] * 100 >= thresholds["hire"])
    review_count = sum(1 for c in results if thresholds["review"] <= c["score"] * 100 < thresholds["hire"])
    reject_count = sum(1 for c in results if c["score"] * 100 < thresholds["review"])
    avg_score = np.mean([c["score"] * 100 for c in results])

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total", total)
    c2.metric("Hire", hire_count, help=f"Score ≥ {thresholds['hire']}")
    c3.metric("Review", review_count, help=f"Score {thresholds['review']}-{thresholds['hire']}")
    c4.metric("Reject", reject_count, help=f"Score < {thresholds['review']}")
    c5.metric("Avg Score", f"{avg_score:.1f}")

    st.divider()

    # =========================
    # Charts Row 1
    # =========================

    left, right = st.columns(2)

    with left:
        st.subheader("📈 Score Distribution")

        scores = [c["score"] * 100 for c in results]

        fig = px.histogram(
            x=scores,
            nbins=25,
            template="plotly_dark",
            color_discrete_sequence=["#00D4FF"],
            labels={"x": "AI Score", "count": "Count"},
        )
        # Add threshold lines
        fig.add_vline(x=thresholds["hire"], line_dash="dash", line_color="#35d49a",
                      annotation_text="Hire")
        fig.add_vline(x=thresholds["review"], line_dash="dash", line_color="#ffc857",
                      annotation_text="Review")
        fig.update_layout(xaxis_title="AI Score", yaxis_title="Candidates")
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("🥧 Decision Breakdown")

        pie = pd.DataFrame({
            "Decision": ["Hire", "Review", "Reject"],
            "Count": [hire_count, review_count, reject_count],
            "Color": ["#35d49a", "#ffc857", "#ff6b81"],
        })

        fig = px.pie(
            pie,
            names="Decision",
            values="Count",
            hole=0.65,
            template="plotly_dark",
            color="Decision",
            color_discrete_map={"Hire": "#35d49a", "Review": "#ffc857", "Reject": "#ff6b81"},
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # =========================
    # Charts Row 2
    # =========================

    left2, right2 = st.columns(2)

    with left2:
        st.subheader("💼 Experience Distribution")

        experiences = [c["years_of_experience"] for c in results]

        fig = px.histogram(
            x=experiences,
            nbins=15,
            template="plotly_dark",
            color_discrete_sequence=["#35d49a"],
            labels={"x": "Years", "count": "Count"},
        )
        # Add JD preference range
        fig.add_vrect(x0=5, x1=9, fillcolor="#00D4FF", opacity=0.1,
                      annotation_text="JD Range (5-9y)")
        fig.update_layout(xaxis_title="Years of Experience", yaxis_title="Candidates")
        st.plotly_chart(fig, use_container_width=True)

    with right2:
        st.subheader("🛡 Trust Score Distribution")

        trust_scores = [c["trust_score"] * 100 for c in results]

        fig = px.histogram(
            x=trust_scores,
            nbins=20,
            template="plotly_dark",
            color_discrete_sequence=["#ff6b6b"],
            labels={"x": "Trust %", "count": "Count"},
        )
        fig.update_layout(xaxis_title="Trust Score (%)", yaxis_title="Candidates")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # =========================
    # Location Analysis - LIVE
    # =========================

    st.subheader("🌍 Location Distribution")

    locations = [c["location"] or c["country"] or "Unknown" for c in results]
    loc_counts = pd.Series(locations).value_counts().head(12)

    if not loc_counts.empty:
        loc_df = pd.DataFrame({
            "Location": loc_counts.index,
            "Candidates": loc_counts.values,
        })

        fig = px.bar(
            loc_df,
            x="Candidates",
            y="Location",
            orientation="h",
            template="plotly_dark",
            color="Candidates",
            color_continuous_scale=["#182746", "#00D4FF"],
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # =========================
    # Score vs Experience Scatter
    # =========================

    st.subheader("🎯 Score vs Experience")

    scatter_df = pd.DataFrame({
        "Score": [c["score"] * 100 for c in results],
        "Experience": [c["years_of_experience"] for c in results],
        "Trust": [c["trust_score"] * 100 for c in results],
        "Decision": [
            "Hire" if c["score"] * 100 >= thresholds["hire"]
            else "Review" if c["score"] * 100 >= thresholds["review"]
            else "Reject"
            for c in results
        ],
    })

    fig = px.scatter(
        scatter_df,
        x="Experience",
        y="Score",
        color="Decision",
        size="Trust",
        template="plotly_dark",
        color_discrete_map={"Hire": "#35d49a", "Review": "#ffc857", "Reject": "#ff6b81"},
        hover_data=["Trust"],
    )
    fig.update_layout(xaxis_title="Years of Experience", yaxis_title="AI Score")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # =========================
    # Skill Analysis - from uploaded candidates
    # =========================

    if candidates_raw:
        st.subheader("🔥 Top Skills Across Candidates")

        all_skills = []
        for cand in candidates_raw:
            skills = cand.get("skills", [])
            for s in skills:
                if isinstance(s, dict):
                    all_skills.append(s.get("name", "Unknown"))
                elif isinstance(s, str):
                    all_skills.append(s)

        if all_skills:
            skill_counts = pd.Series(all_skills).value_counts().head(15)
            skills_df = pd.DataFrame({
                "Skill": skill_counts.index,
                "Candidates": skill_counts.values,
            })

            fig = px.bar(
                skills_df,
                x="Candidates",
                y="Skill",
                orientation="h",
                template="plotly_dark",
                color="Candidates",
                color_continuous_scale=["#182746", "#4f8cff"],
            )
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # =========================
    # AI Insights - LIVE
    # =========================

    st.subheader("🤖 AI Insights")

    honeypots = metadata.get("honeypots_filtered", 0)
    runtime = metadata.get("runtime_seconds", 0)

    icol1, icol2 = st.columns(2)

    with icol1:
        st.success(f"✔ {hire_count} candidates recommended for hire (≥ {thresholds['hire']})")
        st.info(f"📈 Average AI score: {avg_score:.1f}")
        st.info(f"⚡ Ranking completed in {runtime}s")

        # Top performer insight
        if results:
            top = results[0]
            st.success(
                f"🏆 Top candidate: {top['candidate_id']} — "
                f"{top['title']} @ {top['company']} (score: {top['score']*100:.1f})"
            )

    with icol2:
        if honeypots > 0:
            st.warning(f"⚠ {honeypots} honeypot profiles were filtered during ranking")

        low_trust = sum(1 for c in results if c["trust_score"] < 0.6)
        if low_trust > 0:
            st.error(f"🚨 {low_trust} candidates have low trust scores (< 60%)")

        # Experience insight
        in_range = sum(1 for c in results if 5 <= c["years_of_experience"] <= 9)
        st.info(f"💼 {in_range}/{len(results)} candidates in target experience range (5-9 yrs)")
