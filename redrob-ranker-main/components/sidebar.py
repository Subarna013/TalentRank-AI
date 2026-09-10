import streamlit as st


def sidebar():
    """Navigation sidebar using native Streamlit — no third-party deps, no network calls."""

    with st.sidebar:

        # Logo
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:10px; padding:12px 4px 20px 4px;">
                <div style="
                    width:38px; height:38px; border-radius:10px;
                    background: linear-gradient(135deg, #4f8cff, #8b5cf6);
                    display:flex; align-items:center; justify-content:center;
                    font-size:20px;
                ">🤖</div>
                <div style="font-size:20px; font-weight:800; color:white; letter-spacing:-0.5px;">RedRob</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Navigation
        page = st.radio(
            "Navigation",
            options=[
                "Dashboard",
                "Candidates",
                "Rankings",
                "AI Insights",
                "Analytics",
                "Fraud Detection",
                "Reports",
                "Upload Resumes",
                "Settings",
                "API Docs",
            ],
            label_visibility="collapsed",
        )

        st.markdown("---")

        # Resumes Processed (from session only — no network calls)
        result = st.session_state.get("ranking_result")
        if result:
            meta = result.get("metadata", {})
            ranked = meta.get("candidates_ranked", 0)
            total = meta.get("total_input", 0)
            st.caption(f"✅ Ranked: **{ranked:,}** / {total:,}")
            st.progress(min(ranked / max(total, 1), 1.0))
        else:
            st.caption("⏳ No data yet")

        st.markdown("---")
        st.caption("👤 Admin · Super Admin")

    return page
