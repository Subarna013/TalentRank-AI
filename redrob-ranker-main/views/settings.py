import streamlit as st
from utils.api_client import get_config, health, is_backend_available


def render():
    st.title("⚙ Settings")
    st.caption("System configuration, thresholds, and session management")

    st.divider()

    # ─── Backend Health Check ───
    st.subheader("🔌 Backend Status")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.session_state["backend_online"] = is_backend_available()
            st.rerun()

    if st.session_state.get("backend_online"):
        try:
            health_data = health()
            st.success("✅ Backend is online and healthy")

            hcol1, hcol2, hcol3, hcol4 = st.columns(4)
            hcol1.metric("Status", health_data.get("status", "unknown"))
            hcol2.metric("Version", health_data.get("version", "unknown"))
            hcol3.metric("Features", health_data.get("features", 0))
            hcol4.metric("Skill Categories", health_data.get("canonical_categories", 0))
        except Exception as e:
            st.error(f"❌ Backend error: {e}")
            st.session_state["backend_online"] = False
    else:
        st.error("❌ Backend is offline. Start the FastAPI server to enable ranking.")
        st.code("uvicorn api.server:app --host 0.0.0.0 --port 8000", language="bash")

    st.divider()

    # ─── Decision Thresholds ───
    st.subheader("🎯 Decision Thresholds")
    st.caption("Configure what score ranges map to Hire / Review / Reject decisions")

    thresholds = st.session_state.get("thresholds", {"hire": 85, "review": 70})

    tcol1, tcol2 = st.columns(2)

    with tcol1:
        new_hire = st.slider(
            "Hire threshold (score ≥ this = HIRE)",
            min_value=50, max_value=100, value=thresholds["hire"],
            help="Candidates scoring at or above this are recommended for hire"
        )

    with tcol2:
        new_review = st.slider(
            "Review threshold (score ≥ this = REVIEW)",
            min_value=30, max_value=new_hire - 1, value=min(thresholds["review"], new_hire - 1),
            help="Candidates between this and the hire threshold need manual review"
        )

    if new_hire != thresholds["hire"] or new_review != thresholds["review"]:
        st.session_state["thresholds"] = {"hire": new_hire, "review": new_review}
        st.success(f"Updated: HIRE ≥ {new_hire}, REVIEW ≥ {new_review}, REJECT < {new_review}")

    st.info(f"Current: **HIRE** ≥ {new_hire} | **REVIEW** ≥ {new_review} | **REJECT** < {new_review}")

    st.divider()

    # ─── Scoring Configuration ───
    st.subheader("📐 Backend Scoring Configuration")

    if st.session_state.get("backend_online"):
        try:
            config = get_config()

            st.markdown(f"**Job Title:** {config.get('jd_title', 'N/A')}")
            st.markdown(f"**Company:** {config.get('jd_company', 'N/A')}")
            st.markdown(f"**Experience Range:** {config.get('experience_range', 'N/A')} years")

            with st.expander("📍 Preferred Locations"):
                locations = config.get("preferred_locations", [])
                st.write(", ".join(locations) if locations else "Not configured")

            with st.expander("🏗 Scoring Architecture"):
                st.info(config.get("scoring_architecture", "N/A"))
                st.markdown("**Ranking Passes:**")
                for p in config.get("passes", []):
                    st.write(f"• {p}")
                st.markdown("**Score Modifiers:**")
                for m in config.get("modifiers", []):
                    st.write(f"• {m}")

        except Exception as e:
            st.warning(f"Could not load configuration: {e}")
    else:
        st.info("Backend offline — configuration unavailable.")

    st.divider()

    # ─── Shortlist Management ───
    st.subheader("⭐ Shortlist")

    shortlisted = st.session_state.get("shortlisted", set())

    if shortlisted:
        st.write(f"**{len(shortlisted)} candidates shortlisted:**")

        result = st.session_state.get("ranking_result")
        if result:
            shortlist_data = [
                c for c in result["results"]
                if c["candidate_id"] in shortlisted
            ]
            if shortlist_data:
                import pandas as pd
                sl_df = pd.DataFrame({
                    "ID": [c["candidate_id"] for c in shortlist_data],
                    "Title": [c["title"] for c in shortlist_data],
                    "Company": [c["company"] for c in shortlist_data],
                    "Score": [round(c["score"] * 100, 1) for c in shortlist_data],
                    "Experience": [c["years_of_experience"] for c in shortlist_data],
                })
                st.dataframe(sl_df, use_container_width=True, hide_index=True)

                # Export shortlist
                csv = sl_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇ Export Shortlist CSV",
                    csv,
                    "shortlisted_candidates.csv",
                    "text/csv",
                    use_container_width=True,
                )

        col_clear, _ = st.columns([1, 3])
        with col_clear:
            if st.button("🗑 Clear Shortlist", type="secondary"):
                st.session_state["shortlisted"] = set()
                st.rerun()
    else:
        st.info("No candidates shortlisted yet. Use the ☆ button on the Leaderboard page.")

    st.divider()

    # ─── Session State Info ───
    st.subheader("📊 Current Session")

    result = st.session_state.get("ranking_result")
    if result:
        meta = result.get("metadata", {})
        st.success("Ranking data loaded in session")

        scol1, scol2, scol3, scol4 = st.columns(4)
        scol1.metric("Candidates Ranked", meta.get("candidates_ranked", 0))
        scol2.metric("Honeypots Filtered", meta.get("honeypots_filtered", 0))
        scol3.metric("Runtime", f"{meta.get('runtime_seconds', 0)}s")
        scol4.metric("Shortlisted", len(shortlisted))

        if st.button("🗑 Clear All Session Data", type="secondary"):
            st.session_state["ranking_result"] = None
            st.session_state["uploaded_candidates"] = None
            st.session_state["shortlisted"] = set()
            st.rerun()
    else:
        st.info("No ranking data in session. Upload a dataset on the Dashboard.")
