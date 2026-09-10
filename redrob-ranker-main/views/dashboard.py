import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from utils.decisions import get_decision_for_rank, get_decision_counts


def render():
    st.markdown("## Welcome back, Admin! 👋")
    st.caption("Here's what's happening with your candidate rankings today.")
    st.divider()

    result = st.session_state.get("ranking_result")

    if not result or not result.get("results"):
        st.info("📂 Go to **Upload Resumes** in the sidebar to upload a candidate dataset and see the AI ranking dashboard.")
        return

    results = result["results"]
    metadata = result.get("metadata", {})
    total = metadata.get("total_input", len(results))
    ranked = len(results)

    # Percentile-based decisions
    decisions = get_decision_counts(results)
    avg_score = np.mean([c["score"] * 100 for c in results])
    fraud = metadata.get("honeypots_filtered", 0)
    low_trust = sum(1 for c in results if c["trust_score"] < 0.6)

    # KPI Row
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("👥 Total Candidates", f"{total:,}")
    k2.metric("📊 Avg. Score", f"{avg_score:.1f}")
    k3.metric("✅ Shortlisted", f"{decisions['hire']}")
    k4.metric("⚠️ Fraud Alerts", f"{fraud + low_trust}")
    k5.metric("🎯 Hire Rate", f"{decisions['hire']/max(ranked,1)*100:.0f}%")

    st.divider()

    # Charts row
    col_chart, col_donut = st.columns([2, 1.5])

    with col_chart:
        st.markdown("**📈 Score Distribution**")
        scores = [c["score"] * 100 for c in results]
        bins = ["0-20", "20-40", "40-60", "60-80", "80-100"]
        bin_edges = [0, 20, 40, 60, 80, 100]
        counts = [sum(1 for s in scores if bin_edges[i] <= s < bin_edges[i+1]) for i in range(5)]
        counts[-1] += sum(1 for s in scores if s == 100)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=bins, y=counts,
            marker=dict(color=["#ef4444", "#f59e0b", "#f59e0b", "#4f8cff", "#10b981"]),
        ))
        fig.update_layout(
            template="plotly_dark", height=280,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=30, r=20, t=10, b=40),
            xaxis=dict(title="Score Range", gridcolor="#1e2a45"),
            yaxis=dict(title="Candidates", gridcolor="#1e2a45"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_donut:
        st.markdown("**🎯 AI Decision Breakdown**")
        fig = go.Figure(data=[go.Pie(
            values=[decisions["hire"], decisions["review"], decisions["reject"]],
            labels=[
                f"Hire (Top {st.session_state.get('thresholds',{}).get('hire',10)}%)",
                f"Review (Top {st.session_state.get('thresholds',{}).get('review',30)}%)",
                "Reject"
            ],
            hole=0.7,
            marker=dict(colors=["#10b981", "#f59e0b", "#ef4444"]),
            textinfo="none",
        )])
        fig.update_layout(
            template="plotly_dark", height=280,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True,
            legend=dict(font=dict(size=10, color="#94a3b8")),
            annotations=[dict(text=f"<b>{ranked}</b><br>Ranked", x=0.5, y=0.5, font=dict(size=16, color="white"), showarrow=False)],
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Top candidates + Fraud
    col_table, col_fraud = st.columns([3, 2])

    with col_table:
        st.markdown("**🏆 Top Ranked Candidates**")
        top_n = results[:10]
        table_data = []
        for i, c in enumerate(top_n):
            decision = get_decision_for_rank(i + 1, ranked, c["score"])
            table_data.append({
                "#": i + 1,
                "Candidate": c["candidate_id"],
                "Title": c["title"],
                "Company": c["company"],
                "Score": round(c["score"] * 100, 1),
                "Exp": f"{c['years_of_experience']}y",
                "Decision": decision,
            })
        st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

    with col_fraud:
        st.markdown("**🛡 Fraud Detection**")
        total_alerts = fraud + low_trust
        safe = ranked - total_alerts

        fig = go.Figure(data=[go.Pie(
            values=[max(fraud, 0), max(low_trust, 0), max(safe, 1)],
            labels=["Honeypots", "Low Trust", "Verified"],
            hole=0.75,
            marker=dict(colors=["#ef4444", "#f59e0b", "#10b981"]),
            textinfo="none",
        )])
        fig.update_layout(
            template="plotly_dark", height=220,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=10),
            annotations=[dict(text=f"<b>{total_alerts}</b><br>Alerts", x=0.5, y=0.5, font=dict(size=16, color="white"), showarrow=False)],
        )
        st.plotly_chart(fig, use_container_width=True)

        if total_alerts == 0:
            st.success("✅ All candidates verified")
        else:
            st.warning(f"⚠️ {total_alerts} candidates need review")

    st.divider()

    # Bottom stats
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("📄 Processed", f"{total:,}")
    s2.metric("⚡ Runtime", f"{metadata.get('runtime_seconds', 0)}s")
    s3.metric("🏆 Top Score", f"{results[0]['score']*100:.1f}")
    s4.metric("📊 Median", f"{results[ranked//2]['score']*100:.1f}")
