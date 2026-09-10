"""
Decision logic for candidate classification.

Uses a HYBRID approach:
1. Absolute minimum score threshold (quality gate) — no one gets hired below this
2. Within qualified candidates, uses percentile ranking

This prevents the "best of a bad batch" problem:
- If ALL candidates score below 50, none get "Hire" even if they're top-ranked
- The system won't recommend someone with 30% score just because they're #1

Industry standard thresholds:
- Hire: Score >= 60 AND in top 15% of pool
- Review: Score >= 35 AND in top 40% of pool  
- Reject: Everyone else
"""
import streamlit as st


# Absolute minimum scores — non-negotiable quality gates
MIN_SCORE_HIRE = 60      # Must score at least 60% to even be considered for hire
MIN_SCORE_REVIEW = 35    # Must score at least 35% to avoid immediate rejection


def get_decision_for_rank(rank: int, total: int, score: float = None) -> str:
    """
    Determine decision using hybrid logic:
    - Must pass absolute score threshold
    - AND be in the right percentile
    """
    if total == 0:
        return "❌ Reject"

    thresholds = st.session_state.get("thresholds", {"hire": 15, "review": 40})
    percentile = (rank / total) * 100

    # Convert score from 0-1 to 0-100 if needed
    if score is not None and score <= 1.0:
        score_pct = score * 100
    elif score is not None:
        score_pct = score
    else:
        score_pct = 0

    # HYBRID: Must pass BOTH the quality gate AND percentile cutoff
    if score_pct >= MIN_SCORE_HIRE and percentile <= thresholds["hire"]:
        return "✅ Hire"
    elif score_pct >= MIN_SCORE_REVIEW and percentile <= thresholds["review"]:
        return "🔍 Review"
    else:
        return "❌ Reject"


def get_decision_counts(results: list) -> dict:
    """Get counts for each decision category."""
    if not results:
        return {"hire": 0, "review": 0, "reject": 0}

    total = len(results)
    hire = 0
    review = 0
    reject = 0

    for i, c in enumerate(results):
        decision = get_decision_for_rank(i + 1, total, c["score"])
        if "Hire" in decision:
            hire += 1
        elif "Review" in decision:
            review += 1
        else:
            reject += 1

    return {"hire": hire, "review": review, "reject": reject}


def get_decision_label(rank: int, total: int, score: float = None) -> tuple:
    """Returns (label, emoji, color) for a given rank."""
    decision = get_decision_for_rank(rank, total, score)
    if "Hire" in decision:
        return "Hire", "✅", "#10b981"
    elif "Review" in decision:
        return "Review", "🔍", "#f59e0b"
    else:
        return "Reject", "❌", "#ef4444"
