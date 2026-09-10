"""
Behavioral Feature Family.

Extracts engagement, availability, trust, and recruiter interest signals
from the redrob_signals object. These signals are modifiers on top of
skill matching — they determine whether a theoretically good candidate
is actually available and engageable.
"""
from datetime import date, datetime
from typing import Dict

from src.config.settings import Settings, get_settings


class BehavioralFeatureExtractor:
    """Extract behavioral/engagement features from Redrob signals."""

    def __init__(self, settings: Settings = None):
        self.settings = settings or get_settings()
        self.reference_date = date(2026, 6, 27)

    def extract(self, signals: Dict) -> Dict[str, float]:
        """Extract all behavioral features from redrob_signals."""
        features = {}

        # 1. Engagement Score (is this person active on the platform?)
        features["engagement_score"] = self._compute_engagement(signals)

        # 2. Availability Score (can we actually hire them?)
        features["availability_score"] = self._compute_availability(signals)

        # 3. Platform Trust Score (are they verified and legitimate?)
        features["platform_trust_score"] = self._compute_platform_trust(signals)

        # 4. Recruiter Interest Score (are other recruiters interested?)
        features["recruiter_interest_score"] = self._compute_recruiter_interest(signals)

        # 5. Raw signal features
        features["response_rate"] = signals.get("recruiter_response_rate", 0.0)
        features["notice_period_days"] = signals.get("notice_period_days", 180)
        features["open_to_work"] = float(signals.get("open_to_work_flag", False))
        features["last_active_recency_days"] = self._days_since_active(signals)
        features["profile_completeness"] = signals.get("profile_completeness_score", 0.0) / 100.0
        features["github_activity_score"] = max(
            signals.get("github_activity_score", -1), 0.0
        ) / 100.0

        # 6. Verification Score
        features["verification_score"] = self._compute_verification(signals)

        return features

    def _compute_engagement(self, signals: Dict) -> float:
        """
        Composite engagement score. A candidate who is active, responsive,
        and completing interviews is more likely to be hireable.
        """
        components = []

        # Recency of activity (most important)
        days_since_active = self._days_since_active(signals)
        if days_since_active <= 7:
            recency_score = 1.0
        elif days_since_active <= 30:
            recency_score = 0.8
        elif days_since_active <= 90:
            recency_score = 0.5
        elif days_since_active <= 180:
            recency_score = 0.2
        else:
            recency_score = 0.0
        components.append(("recency", recency_score, 0.35))

        # Response rate
        response_rate = signals.get("recruiter_response_rate", 0.0)
        components.append(("response_rate", response_rate, 0.25))

        # Interview completion rate
        interview_rate = signals.get("interview_completion_rate", 0.0)
        components.append(("interview_completion", interview_rate, 0.20))

        # Open to work flag
        open_to_work = float(signals.get("open_to_work_flag", False))
        components.append(("open_to_work", open_to_work, 0.10))

        # Applications submitted (shows active job search)
        apps = signals.get("applications_submitted_30d", 0)
        apps_score = min(apps / 5.0, 1.0)  # normalize: 5+ apps = max
        components.append(("applications", apps_score, 0.10))

        # Weighted sum
        score = sum(value * weight for _, value, weight in components)
        return min(max(score, 0.0), 1.0)

    def _compute_availability(self, signals: Dict) -> float:
        """
        Can we actually hire this person? Considers notice period,
        salary expectations, work mode, relocation willingness.
        """
        components = []

        # Notice period (JD prefers <30 days, accepts up to 90)
        notice = signals.get("notice_period_days", 180)
        if notice <= 30:
            notice_score = 1.0
        elif notice <= 60:
            notice_score = 0.7
        elif notice <= 90:
            notice_score = 0.4
        else:
            notice_score = 0.1
        components.append(("notice", notice_score, 0.35))

        # Work mode preference
        preferred_mode = signals.get("preferred_work_mode", "onsite")
        jd_modes = {"hybrid", "onsite", "flexible"}
        if preferred_mode in jd_modes:
            mode_score = 1.0
        elif preferred_mode == "remote":
            mode_score = 0.4  # JD is hybrid, remote-only is a gap
        else:
            mode_score = 0.6
        components.append(("work_mode", mode_score, 0.20))

        # Willing to relocate
        relocate = float(signals.get("willing_to_relocate", False))
        components.append(("relocate", relocate, 0.15))

        # Offer acceptance rate (historical hiring success)
        offer_rate = signals.get("offer_acceptance_rate", -1)
        if offer_rate >= 0:
            components.append(("offer_rate", offer_rate, 0.15))
        else:
            components.append(("offer_rate", 0.5, 0.15))  # neutral if no history

        # Response time (faster = more available)
        response_time = signals.get("avg_response_time_hours", 168)
        if response_time <= 24:
            time_score = 1.0
        elif response_time <= 48:
            time_score = 0.8
        elif response_time <= 96:
            time_score = 0.5
        else:
            time_score = 0.2
        components.append(("response_time", time_score, 0.15))

        score = sum(value * weight for _, value, weight in components)
        return min(max(score, 0.0), 1.0)

    def _compute_platform_trust(self, signals: Dict) -> float:
        """
        Trust score based on profile completeness, verification,
        and platform engagement depth.
        """
        components = []

        # Profile completeness
        completeness = signals.get("profile_completeness_score", 0.0) / 100.0
        components.append(("completeness", completeness, 0.25))

        # Verification
        verified_email = float(signals.get("verified_email", False))
        verified_phone = float(signals.get("verified_phone", False))
        linkedin = float(signals.get("linkedin_connected", False))
        verification = (verified_email + verified_phone + linkedin) / 3.0
        components.append(("verification", verification, 0.30))

        # Connection count (shows genuine platform usage)
        connections = signals.get("connection_count", 0)
        connection_score = min(connections / 500.0, 1.0)
        components.append(("connections", connection_score, 0.15))

        # Endorsements received
        endorsements = signals.get("endorsements_received", 0)
        endorse_score = min(endorsements / 50.0, 1.0)
        components.append(("endorsements", endorse_score, 0.15))

        # GitHub activity
        github = signals.get("github_activity_score", -1)
        if github >= 0:
            github_score = github / 100.0
        else:
            github_score = 0.3  # neutral if no GitHub
        components.append(("github", github_score, 0.15))

        score = sum(value * weight for _, value, weight in components)
        return min(max(score, 0.0), 1.0)

    def _compute_recruiter_interest(self, signals: Dict) -> float:
        """
        Are other recruiters interested in this candidate?
        High recruiter interest = market validation of candidate quality.
        """
        components = []

        # Profile views
        views = signals.get("profile_views_received_30d", 0)
        views_score = min(views / 30.0, 1.0)
        components.append(("views", views_score, 0.25))

        # Search appearances
        appearances = signals.get("search_appearance_30d", 0)
        appearance_score = min(appearances / 200.0, 1.0)
        components.append(("appearances", appearance_score, 0.25))

        # Saved by recruiters
        saved = signals.get("saved_by_recruiters_30d", 0)
        saved_score = min(saved / 10.0, 1.0)
        components.append(("saved", saved_score, 0.30))

        # Endorsements received (peer validation)
        endorsements = signals.get("endorsements_received", 0)
        endorse_score = min(endorsements / 50.0, 1.0)
        components.append(("endorsements", endorse_score, 0.20))

        score = sum(value * weight for _, value, weight in components)
        return min(max(score, 0.0), 1.0)

    def _compute_verification(self, signals: Dict) -> float:
        """Simple verification score."""
        verified_email = float(signals.get("verified_email", False))
        verified_phone = float(signals.get("verified_phone", False))
        linkedin = float(signals.get("linkedin_connected", False))
        return (verified_email + verified_phone + linkedin) / 3.0

    def _days_since_active(self, signals: Dict) -> int:
        """Compute days since last active."""
        last_active = signals.get("last_active_date")
        if not last_active:
            return 365  # assume inactive

        try:
            active_date = datetime.strptime(str(last_active), "%Y-%m-%d").date()
            delta = (self.reference_date - active_date).days
            return max(delta, 0)
        except (ValueError, TypeError):
            return 365
