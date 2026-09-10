import streamlit as st


def kpi_card(icon: str, label: str, value, color: str = "blue", change: str = None):
    """Render a KPI card using st.metric inside a styled container."""
    st.metric(label=f"{icon} {label}", value=value, delta=change)


def metric_card(icon, title, value, change=None):
    """Legacy wrapper."""
    kpi_card(icon, title, value, "cyan", change)


def stats_bar(items: list):
    """Render stats as columns of metrics."""
    cols = st.columns(len(items))
    for i, item in enumerate(items):
        with cols[i]:
            st.metric(
                label=f"{item['icon']} {item['label']}",
                value=item["value"]
            )


def ai_insight_panel(title: str, items: list):
    """Render AI insights as info boxes."""
    st.markdown(f"#### 🤖 {title}")
    for item in items:
        st.info(f"**{item['label']}:** {item['text']}")


def candidate_table_row(rank: int, name: str, subtitle: str, score: float,
                         skills_match: str, confidence: str, status: str,
                         avatar_color: str = "#4f8cff"):
    """Return candidate data as a dict for DataFrame rendering."""
    return {
        "Rank": rank,
        "Candidate": name,
        "Role": subtitle,
        "Score": f"{score:.1f}",
        "Skills": skills_match,
        "Confidence": confidence,
        "Status": status,
    }
