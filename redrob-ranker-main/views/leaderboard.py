import streamlit as st
import pandas as pd
from utils.decisions import get_decision_for_rank


def render():
    st.markdown("## 🏆 Candidate Rankings")
    st.caption("Search, filter, and shortlist candidates from AI rankings.")
    st.divider()

    result = st.session_state.get("ranking_result")

    if not result or not result.get("results"):
        st.warning("⚠ No ranking results available. Please upload a dataset on the **Upload Resumes** page first.")
        return

    results = result["results"]
    total = len(results)

    # Controls
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        search = st.text_input("🔍 Search by title, company, ID, or location", "")
    with col2:
        min_score = st.slider("Min Score", 0, 100, 0)
    with col3:
        sort_by = st.selectbox("Sort by", ["Rank", "Score ↓", "Experience ↓", "Trust ↓"])
    with col4:
        decision_filter = st.selectbox("Decision", ["All", "Hire", "Review", "Reject"])

    # Filter
    filtered = []
    for i, c in enumerate(results):
        score_pct = c["score"] * 100
        rank = i + 1
        decision = get_decision_for_rank(rank, total, c["score"])

        if score_pct < min_score:
            continue
        if search:
            searchable = f"{c['title']} {c['company']} {c['candidate_id']} {c['location']} {c['country']}".lower()
            if search.lower() not in searchable:
                continue
        if decision_filter == "Hire" and "Hire" not in decision:
            continue
        elif decision_filter == "Review" and "Review" not in decision:
            continue
        elif decision_filter == "Reject" and "Reject" not in decision:
            continue

        filtered.append((rank, c, decision))

    # Sort
    if sort_by == "Score ↓":
        filtered.sort(key=lambda x: -x[1]["score"])
    elif sort_by == "Experience ↓":
        filtered.sort(key=lambda x: -x[1]["years_of_experience"])
    elif sort_by == "Trust ↓":
        filtered.sort(key=lambda x: -x[1]["trust_score"])

    # Pagination
    PAGE_SIZE = 20
    total_pages = max(1, (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE)

    col_info, col_page = st.columns([3, 1])
    with col_info:
        shortlisted_count = len(st.session_state.get("shortlisted", set()))
        st.caption(f"Showing {len(filtered)} of {total} candidates | ⭐ {shortlisted_count} shortlisted")
    with col_page:
        current_page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, label_visibility="collapsed")

    start_idx = (current_page - 1) * PAGE_SIZE
    page_items = filtered[start_idx:start_idx + PAGE_SIZE]

    st.caption(f"Page {current_page} of {total_pages}")
    st.divider()

    # Display
    medals = ["🥇", "🥈", "🥉"]

    for rank, c, decision in page_items:
        score_pct = c["score"] * 100
        trust_pct = c["trust_score"] * 100
        cid = c["candidate_id"]
        medal = medals[rank-1] if rank <= 3 else f"**#{rank}**"
        is_shortlisted = cid in st.session_state.get("shortlisted", set())

        with st.container(border=True):
            left, mid, right = st.columns([3, 2, 1])

            with left:
                st.markdown(f"### {medal} {cid}")
                st.caption(f"{c['title']} @ {c['company']}")
                s1, s2, s3 = st.columns(3)
                s1.metric("AI Score", f"{score_pct:.1f}")
                s2.metric("Experience", f"{c['years_of_experience']} yrs")
                s3.metric("Location", c["location"] or c["country"] or "—")

            with mid:
                st.metric("Trust", f"{trust_pct:.1f}%")
                st.progress(c["score"])
                if "Hire" in decision:
                    st.success(decision)
                elif "Review" in decision:
                    st.warning(decision)
                else:
                    st.error(decision)

            with right:
                if is_shortlisted:
                    if st.button("⭐ Remove", key=f"unstar_{cid}", use_container_width=True):
                        st.session_state["shortlisted"].discard(cid)
                        st.rerun()
                else:
                    if st.button("☆ Shortlist", key=f"star_{cid}", use_container_width=True):
                        st.session_state["shortlisted"].add(cid)
                        st.rerun()

            with st.expander("💡 AI Reasoning"):
                st.write(c.get("reasoning", "No reasoning available."))

    # Summary
    if filtered:
        st.divider()
        avg = sum(x[1]["score"] for x in filtered) / len(filtered) * 100
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Avg Score", f"{avg:.1f}")
        col_b.metric("Showing", len(filtered))
        col_c.metric("Shortlisted", shortlisted_count)
