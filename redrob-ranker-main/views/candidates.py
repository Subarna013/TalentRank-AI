import streamlit as st
import plotly.graph_objects as go
from utils.api_client import explain_candidate


def render():
    st.markdown("""
    <div class="welcome-header">
        <div class="welcome-text">
            <h2>👥 Candidates</h2>
            <p>Browse and view detailed profiles of all ranked candidates.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Get live data
    result = st.session_state.get("ranking_result")
    candidates_raw = st.session_state.get("uploaded_candidates")

    if not result or not result.get("results"):
        st.warning("⚠ No ranking results available. Upload a dataset on the **Upload Resumes** page first.")
        st.stop()

    results = result["results"]
    thresholds = st.session_state.get("thresholds", {"hire": 85, "review": 70})
    shortlisted = st.session_state.get("shortlisted", set())

    # Build candidate lookup
    candidate_lookup = {}
    if candidates_raw:
        for raw in candidates_raw:
            cid = raw.get("candidate_id", "")
            candidate_lookup[cid] = raw

    # ─── Search and Filter Bar ───
    col_search, col_filter = st.columns([3, 1])
    with col_search:
        search = st.text_input("🔍 Search candidates...", "", placeholder="Search by ID, title, company, location")
    with col_filter:
        view_mode = st.selectbox("View", ["Card View", "Table View"])

    # Filter
    filtered = results
    if search:
        search_lower = search.lower()
        filtered = [
            c for c in results
            if search_lower in f"{c['candidate_id']} {c['title']} {c['company']} {c['location']}".lower()
        ]

    st.caption(f"Showing {len(filtered)} candidates")
    st.divider()

    if view_mode == "Table View":
        # Table view
        import pandas as pd
        df = pd.DataFrame({
            "Rank": [c["rank"] for c in filtered[:100]],
            "ID": [c["candidate_id"] for c in filtered[:100]],
            "Title": [c["title"] for c in filtered[:100]],
            "Company": [c["company"] for c in filtered[:100]],
            "Score": [f"{c['score']*100:.1f}" for c in filtered[:100]],
            "Experience": [f"{c['years_of_experience']} yrs" for c in filtered[:100]],
            "Location": [c["location"] or c["country"] for c in filtered[:100]],
            "Trust": [f"{c['trust_score']*100:.0f}%" for c in filtered[:100]],
            "Status": [
                "✅ Hire" if c["score"]*100 >= thresholds["hire"]
                else "🔍 Review" if c["score"]*100 >= thresholds["review"]
                else "❌ Reject"
                for c in filtered[:100]
            ],
        })
        st.dataframe(df, use_container_width=True, hide_index=True, height=600)

    else:
        # Card view with expandable detail
        for i, c in enumerate(filtered[:30]):
            score_pct = c["score"] * 100
            trust_pct = c["trust_score"] * 100
            cid = c["candidate_id"]
            is_shortlisted = cid in shortlisted

            with st.container(border=True):
                # Header row
                top_left, top_mid, top_right = st.columns([3, 2, 1])

                with top_left:
                    # Avatar + name
                    color = "#10b981" if score_pct >= thresholds["hire"] else "#f59e0b" if score_pct >= thresholds["review"] else "#ef4444"
                    st.markdown(f"""
                    <div style="display:flex; align-items:center; gap:12px;">
                        <div style="width:42px; height:42px; border-radius:50%; background:{color}; display:flex; align-items:center; justify-content:center; font-size:14px; font-weight:700; color:white;">#{c['rank']}</div>
                        <div>
                            <div style="font-size:14px; font-weight:600; color:white;">{cid}</div>
                            <div style="font-size:12px; color:#64748b;">{c['title']} @ {c['company']}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with top_mid:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Score", f"{score_pct:.1f}")
                    m2.metric("Exp", f"{c['years_of_experience']}y")
                    m3.metric("Trust", f"{trust_pct:.0f}%")

                with top_right:
                    if is_shortlisted:
                        if st.button("⭐", key=f"unstar_{cid}_{i}", help="Remove from shortlist"):
                            st.session_state["shortlisted"].discard(cid)
                            st.rerun()
                    else:
                        if st.button("☆", key=f"star_{cid}_{i}", help="Add to shortlist"):
                            st.session_state["shortlisted"].add(cid)
                            st.rerun()

                # Expandable detail
                with st.expander("📋 View Full Profile"):
                    raw = candidate_lookup.get(cid)

                    if raw:
                        detail_left, detail_right = st.columns(2)

                        with detail_left:
                            st.markdown("**Profile**")
                            profile = raw.get("profile", {})
                            st.write(f"- **Headline:** {profile.get('headline', '—')}")
                            st.write(f"- **Location:** {profile.get('location', '—')}, {profile.get('country', '—')}")
                            st.write(f"- **Industry:** {profile.get('current_industry', '—')}")
                            st.write(f"- **Company Size:** {profile.get('current_company_size', '—')}")

                            if profile.get("summary"):
                                st.markdown("**Summary**")
                                st.write(profile["summary"][:300])

                            # Skills
                            skills = raw.get("skills", [])
                            if skills:
                                st.markdown("**Skills**")
                                skill_names = [s.get("name", s) if isinstance(s, dict) else s for s in skills[:15]]
                                st.write(", ".join(skill_names))

                        with detail_right:
                            st.markdown("**Career History**")
                            for job in raw.get("career_history", [])[:3]:
                                duration = job.get("duration_months", 0)
                                st.write(f"- **{job.get('title', '—')}** at {job.get('company', '—')} ({duration} months)")

                            st.markdown("**Education**")
                            for edu in raw.get("education", [])[:2]:
                                st.write(f"- {edu.get('degree', '—')} in {edu.get('field_of_study', '—')} @ {edu.get('institution', '—')}")

                            st.markdown("**AI Reasoning**")
                            st.info(c.get("reasoning", "No reasoning available."))

                    else:
                        st.info("Raw profile data not available for this candidate.")
