import streamlit as st
import pandas as pd
import json


def render():
    st.title("📄 Export Center")
    st.caption("Download ranking reports, shortlists, and detailed analysis")

    st.divider()

    # Get live data from session state
    result = st.session_state.get("ranking_result")

    if not result or not result.get("results"):
        st.warning("⚠ No ranking results available. Please upload a dataset on the **Upload Resumes** page first.")
        st.stop()

    results = result["results"]
    metadata = result.get("metadata", {})
    thresholds = st.session_state.get("thresholds", {"hire": 85, "review": 70})
    shortlisted = st.session_state.get("shortlisted", set())

    # ─── Summary ───
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Ranked", metadata.get("candidates_ranked", len(results)))
    col2.metric("Honeypots Filtered", metadata.get("honeypots_filtered", 0))
    col3.metric("Shortlisted", len(shortlisted))
    col4.metric("Runtime", f"{metadata.get('runtime_seconds', 0)}s")

    st.divider()

    # ─── Export Scope Selection ───
    st.subheader("📋 Select Export Scope")

    export_scope = st.radio(
        "What to export:",
        ["All Ranked Candidates", "Shortlisted Only", "Hire Decisions Only", "Custom Filter"],
        horizontal=True,
    )

    if export_scope == "All Ranked Candidates":
        export_results = results
    elif export_scope == "Shortlisted Only":
        export_results = [c for c in results if c["candidate_id"] in shortlisted]
        if not export_results:
            st.warning("No candidates shortlisted. Use the Leaderboard to shortlist candidates.")
            st.stop()
    elif export_scope == "Hire Decisions Only":
        export_results = [c for c in results if c["score"] * 100 >= thresholds["hire"]]
    elif export_scope == "Custom Filter":
        custom_min = st.slider("Minimum score to export", 0, 100, 0)
        export_results = [c for c in results if c["score"] * 100 >= custom_min]

    st.caption(f"📊 {len(export_results)} candidates in export")

    st.divider()

    # ─── Build Export Data ───
    export_df = pd.DataFrame({
        "Rank": [c["rank"] for c in export_results],
        "Candidate ID": [c["candidate_id"] for c in export_results],
        "Title": [c["title"] for c in export_results],
        "Company": [c["company"] for c in export_results],
        "Score": [round(c["score"] * 100, 2) for c in export_results],
        "Experience (yrs)": [c["years_of_experience"] for c in export_results],
        "Location": [c["location"] for c in export_results],
        "Country": [c["country"] for c in export_results],
        "Trust Score (%)": [round(c["trust_score"] * 100, 2) for c in export_results],
        "Decision": [
            "Hire" if c["score"] * 100 >= thresholds["hire"]
            else "Review" if c["score"] * 100 >= thresholds["review"]
            else "Reject"
            for c in export_results
        ],
        "Shortlisted": ["⭐" if c["candidate_id"] in shortlisted else "" for c in export_results],
        "Reasoning": [c["reasoning"] for c in export_results],
    })

    # ─── Preview Table ───
    st.subheader("📋 Export Preview")
    st.dataframe(
        export_df.head(20),
        use_container_width=True,
        hide_index=True,
    )
    if len(export_df) > 20:
        st.caption(f"Showing first 20 of {len(export_df)} rows")

    st.divider()

    # ─── Download Buttons ───
    st.subheader("⬇ Download")

    col1, col2, col3 = st.columns(3)

    with col1:
        csv_data = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📄 Download CSV",
            csv_data,
            "redrob_ranking.csv",
            "text/csv",
            use_container_width=True,
        )

    with col2:
        # JSON export with full details
        json_export = {
            "metadata": metadata,
            "thresholds": thresholds,
            "export_scope": export_scope,
            "candidates": export_results,
        }
        json_data = json.dumps(json_export, indent=2, default=str).encode("utf-8")
        st.download_button(
            "📋 Download JSON",
            json_data,
            "redrob_ranking.json",
            "application/json",
            use_container_width=True,
        )

    with col3:
        try:
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                export_df.to_excel(writer, index=False, sheet_name="Rankings")

                # Add summary sheet
                summary_df = pd.DataFrame({
                    "Metric": ["Total Ranked", "Hire", "Review", "Reject",
                               "Honeypots Filtered", "Avg Score", "Shortlisted"],
                    "Value": [
                        len(export_results),
                        sum(1 for c in export_results if c["score"] * 100 >= thresholds["hire"]),
                        sum(1 for c in export_results if thresholds["review"] <= c["score"] * 100 < thresholds["hire"]),
                        sum(1 for c in export_results if c["score"] * 100 < thresholds["review"]),
                        metadata.get("honeypots_filtered", 0),
                        f"{sum(c['score'] for c in export_results) / max(len(export_results), 1) * 100:.1f}",
                        len(shortlisted),
                    ],
                })
                summary_df.to_excel(writer, index=False, sheet_name="Summary")

            excel_data = buffer.getvalue()
            st.download_button(
                "📊 Download Excel",
                excel_data,
                "redrob_ranking.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except ImportError:
            st.button("📊 Excel (install openpyxl)", disabled=True, use_container_width=True)

    st.divider()

    # ─── Submission Format ───
    st.subheader("🏆 Competition Submission Format")
    st.caption("Generate a submission.csv in the format required for the Redrob Hackathon")

    submission_df = pd.DataFrame({
        "candidate_id": [c["candidate_id"] for c in export_results],
        "rank": [c["rank"] for c in export_results],
        "score": [round(c["score"], 6) for c in export_results],
    })

    submission_csv = submission_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "🏆 Download submission.csv",
        submission_csv,
        "submission.csv",
        "text/csv",
        use_container_width=True,
    )
