"""
Mutual Interest Scorer.

Inspired by LinkedIn's SIGIR 2018 paper: "We require not just that a candidate
shown must be relevant to the recruiter's query, but also that the candidate
contacted by the recruiter must show interest in the job opportunity."

This module computes the probability that:
1. The candidate is relevant to the JD (quality)
2. The candidate would respond to a recruiter message (engagement)
3. The candidate would accept an offer (hireability)

Final score = quality × engagement × hireability

This multiplicative relationship means even a perfect technical match gets
penalized if they won't respond or won't accept.
"""
from typing import Dict

from src.config.settings import Settings, get_settings


class MutualInterestScorer:
    """
    Computes mutual interest probability between candidate and role.
    
    Key insight from LinkedIn: optimizing for "positive response to recruiter
    message" outperforms optimizing for "relevance to query" alone.
    """

    def __init__(self, settings: Settings = None):
        self.settings = settings or get_settings()

    def compute(self, signals: Dict, profile: Dict) -> Dict[str, float]:
        """
        Compute mutual interest scores.
        
        Returns:
            Dict with individual components and final mutual_interest_score.
        """
        features = {}

        # P(respond) - Will the candidate respond to a recruiter message?
        p_respond = self._compute_response_probability(signals)
        features["p_respond"] = p_respond

        # P(interested) - Is the candidate in a hiring-receptive state?
        p_interested = self._compute_interest_probability(signals, profile)
        features["p_interested"] = p_interested

        # P(hireable) - Given interest, can we actually close them?
        p_hireable = self._compute_hireability(signals, profile)
        features["p_hireable"] = p_hireable

        # Combined mutual interest
        # Use geometric mean-like combination (multiplicative but not too harsh)
        mutual_interest = (
            p_respond ** 0.3 *
            p_interested ** 0.4 *
            p_hireable ** 0.3
        )
        features["mutual_interest_score"] = mutual_interest

        return features

    def _compute_response_probability(self, signals: Dict) -> float:
        """
        Estimate probability the candidate responds to outreach.
        Based on: response rate, response time, activity recency.
        """
        response_rate = signals.get("recruiter_response_rate", 0.0)
        response_time = signals.get("avg_response_time_hours", 168)

        # Response rate is the strongest signal
        # But we dampen extremes — 0% might just mean they're new
        if response_rate >= 0.7:
            p_respond = 0.9
        elif response_rate >= 0.5:
            p_respond = 0.75
        elif response_rate >= 0.3:
            p_respond = 0.55
        elif response_rate >= 0.1:
            p_respond = 0.35
        elif response_rate > 0:
            p_respond = 0.2
        else:
            # Zero response rate — could be new user or unresponsive
            # Check if they have other engagement signals
            views = signals.get("profile_views_received_30d", 0)
            if views > 0:
                p_respond = 0.3  # benefit of doubt
            else:
                p_respond = 0.15

        # Adjust for response time (faster = more likely to respond)
        if response_time <= 24:
            p_respond = min(p_respond * 1.1, 1.0)
        elif response_time >= 168:  # >1 week
            p_respond *= 0.85

        return p_respond

    def _compute_interest_probability(self, signals: Dict, profile: Dict) -> float:
        """
        Estimate probability the candidate is interested in a new role.
        Based on: open_to_work, activity level, application behavior.
        """
        open_to_work = signals.get("open_to_work_flag", False)
        apps_submitted = signals.get("applications_submitted_30d", 0)
        last_active = signals.get("last_active_date", "2024-01-01")
        profile_completeness = signals.get("profile_completeness_score", 0)

        # Open to work is the strongest signal
        if open_to_work:
            base = 0.85
        else:
            base = 0.35  # Many people don't set this flag but are still open

        # Applications submitted boost
        if apps_submitted >= 5:
            base = min(base + 0.15, 0.95)
        elif apps_submitted >= 1:
            base = min(base + 0.05, 0.90)

        # Profile completeness suggests they want to be found
        if profile_completeness >= 80:
            base = min(base + 0.05, 0.95)
        elif profile_completeness < 40:
            base *= 0.85

        # Activity recency
        from datetime import datetime, date
        try:
            active_date = datetime.strptime(str(last_active), "%Y-%m-%d").date()
            days_since = (date(2026, 6, 27) - active_date).days
            if days_since <= 14:
                pass  # fresh activity, keep base
            elif days_since <= 60:
                base *= 0.9
            elif days_since <= 180:
                base *= 0.7
            else:
                base *= 0.4  # inactive for 6+ months
        except (ValueError, TypeError):
            base *= 0.6

        return base

    def _compute_hireability(self, signals: Dict, profile: Dict) -> float:
        """
        Estimate probability we can close this candidate.
        Based on: notice period, salary, location, interview completion rate.
        """
        notice = signals.get("notice_period_days", 90)
        interview_rate = signals.get("interview_completion_rate", 0.5)
        offer_rate = signals.get("offer_acceptance_rate", -1)
        country = profile.get("country", "")

        # Notice period (JD wants <30, accepts up to 90)
        if notice <= 30:
            notice_factor = 1.0
        elif notice <= 60:
            notice_factor = 0.85
        elif notice <= 90:
            notice_factor = 0.65
        elif notice <= 120:
            notice_factor = 0.45
        else:
            notice_factor = 0.25

        # Interview completion rate
        interview_factor = max(interview_rate, 0.3)

        # Offer acceptance rate (if available)
        if offer_rate >= 0:
            offer_factor = 0.5 + 0.5 * offer_rate
        else:
            offer_factor = 0.6  # neutral

        # Location factor (must be hireable in India)
        if country.lower() == "india":
            location_factor = 1.0
        else:
            relocate = signals.get("willing_to_relocate", False)
            location_factor = 0.4 if relocate else 0.15

        # Combine
        hireability = (
            notice_factor * 0.35 +
            interview_factor * 0.25 +
            offer_factor * 0.20 +
            location_factor * 0.20
        )

        return min(max(hireability, 0.0), 1.0)
