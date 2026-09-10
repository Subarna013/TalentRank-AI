"""
Deterministic Explanation Engine.

Generates specific, fact-based reasoning for each ranked candidate.
Key principles:
1. Never hallucinate — every claim references actual profile data
2. Connect to specific JD requirements
3. Acknowledge gaps honestly
4. Vary across candidates (not templated)
5. Tone matches rank position
"""
from typing import Dict, List, Tuple

from src.core.types import Candidate, FeatureVector, RankedCandidate
from src.config.settings import Settings, get_settings


class ExplanationEngine:
    """Generate deterministic, fact-based explanations for rankings."""

    def __init__(self, settings: Settings = None):
        self.settings = settings or get_settings()

    def generate(
        self,
        candidate: Candidate,
        features: FeatureVector,
        rank: int,
        score: float,
    ) -> str:
        """
        Generate a 1-2 sentence reasoning for why this candidate is at this rank.

        The reasoning must:
        - Reference specific facts from the candidate's profile
        - Connect to JD requirements
        - Acknowledge gaps where relevant
        - Not hallucinate skills/experience not in the profile
        """
        # Determine top contributing factors
        strengths = self._identify_strengths(candidate, features)
        concerns = self._identify_concerns(candidate, features)

        # Build reasoning based on rank tier
        if rank <= 10:
            return self._top_tier_reasoning(candidate, features, strengths, concerns)
        elif rank <= 30:
            return self._strong_tier_reasoning(candidate, features, strengths, concerns)
        elif rank <= 60:
            return self._moderate_tier_reasoning(candidate, features, strengths, concerns)
        else:
            return self._lower_tier_reasoning(candidate, features, strengths, concerns)

    def _top_tier_reasoning(
        self,
        candidate: Candidate,
        features: FeatureVector,
        strengths: List[str],
        concerns: List[str],
    ) -> str:
        """Reasoning for ranks 1-10 (strong positive tone with specifics)."""
        parts = []

        # Lead with title + experience
        parts.append(
            f"{candidate.current_title} with {candidate.years_of_experience:.1f} yrs "
            f"at {candidate.current_company}"
        )

        # Skills evidence (be specific about what matters)
        relevant_skills = self._get_relevant_skills(candidate)
        if relevant_skills:
            parts.append(f"core skills: {', '.join(relevant_skills[:4])}")

        # Career evidence
        if features.product_company_ratio > 0.5 and features.career_recency_score > 0.8:
            parts.append("consistent product-company ML career")
        elif features.career_recency_score > 0.8:
            parts.append("currently in directly relevant role")

        # Domain evidence from descriptions
        desc_feats = getattr(features, '_desc_features', {})
        if desc_feats.get("domain_evidence_score", 0) > 0.5:
            parts.append("career shows production retrieval/ranking system work")

        # Behavioral
        if features.engagement_score > 0.7 and features.response_rate > 0.5:
            parts.append(f"highly engaged ({features.response_rate:.0%} response rate)")
        elif features.response_rate > 0.5:
            parts.append(f"responsive ({features.response_rate:.0%})")

        # Location
        if features.location_match:
            loc = candidate.location.split(",")[0] if "," in candidate.location else candidate.location
            parts.append(f"based in {loc}")

        reasoning = "; ".join(parts[:5]) + "."

        # Add minor concern if any (keeps it honest)
        if concerns and len(reasoning) < 180:
            reasoning += f" Note: {concerns[0]}."

        return reasoning

    def _strong_tier_reasoning(
        self,
        candidate: Candidate,
        features: FeatureVector,
        strengths: List[str],
        concerns: List[str],
    ) -> str:
        """Reasoning for ranks 11-30."""
        parts = []

        parts.append(
            f"{candidate.current_title} at {candidate.current_company}"
        )
        parts.append(f"{candidate.years_of_experience:.1f} yrs")

        # Primary strength
        if strengths:
            parts.append(strengths[0])

        # Note what limits them vs top 10
        if concerns:
            parts.append(f"concern: {concerns[0]}")

        return "; ".join(parts[:4]) + "."

    def _moderate_tier_reasoning(
        self,
        candidate: Candidate,
        features: FeatureVector,
        strengths: List[str],
        concerns: List[str],
    ) -> str:
        """Reasoning for ranks 31-60."""
        parts = []

        parts.append(f"{candidate.current_title}, {candidate.years_of_experience:.1f} yrs")

        if strengths:
            parts.append(strengths[0])

        if concerns:
            parts.append(concerns[0])
        else:
            # Generic gap
            if features.title_relevance_score < 0.5:
                parts.append("title not directly aligned with AI/ML engineering")
            elif features.engagement_score < 0.4:
                parts.append("low platform engagement")

        return "; ".join(parts[:3]) + "."

    def _lower_tier_reasoning(
        self,
        candidate: Candidate,
        features: FeatureVector,
        strengths: List[str],
        concerns: List[str],
    ) -> str:
        """Reasoning for ranks 61-100 (frank about limitations)."""
        parts = []

        parts.append(f"{candidate.current_title}, {candidate.years_of_experience:.1f} yrs")

        # Lead with the concern
        if concerns:
            parts.append(concerns[0])
        if len(concerns) > 1:
            parts.append(concerns[1])

        # Mention what got them here at all
        if strengths:
            parts.append(f"included for: {strengths[0]}")

        return "; ".join(parts[:3]) + "."

    def _identify_strengths(
        self, candidate: Candidate, features: FeatureVector
    ) -> List[str]:
        """Identify top strengths based on feature values."""
        strengths = []

        if features.title_relevance_score >= 0.7:
            strengths.append(f"strong title match ({candidate.current_title})")

        if features.skill_semantic_score >= 0.5:
            relevant = self._get_relevant_skills(candidate)
            if relevant:
                strengths.append(f"relevant skills ({', '.join(relevant[:2])})")

        if features.career_recency_score >= 0.8:
            strengths.append("recent relevant work experience")

        if features.product_company_ratio >= 0.6:
            strengths.append("mostly product company experience")

        if features.experience_fit_score >= 0.8:
            strengths.append(f"experience in target range ({candidate.years_of_experience:.1f}y)")

        if features.engagement_score >= 0.7:
            strengths.append("highly active and responsive on platform")

        if features.domain_experience_months >= 36:
            years = features.domain_experience_months / 12
            strengths.append(f"{years:.1f}y domain-relevant experience")

        if features.location_match:
            strengths.append(f"in preferred location ({candidate.location})")

        return strengths

    def _identify_concerns(
        self, candidate: Candidate, features: FeatureVector
    ) -> List[str]:
        """Identify concerns/gaps based on feature values."""
        concerns = []

        if features.title_relevance_score < 0.3:
            concerns.append(f"non-technical title ({candidate.current_title})")

        if features.experience_fit_score < 0.5:
            if candidate.years_of_experience < 4:
                concerns.append(f"below target experience ({candidate.years_of_experience:.1f}y)")
            elif candidate.years_of_experience > 12:
                concerns.append(f"significantly over experience range ({candidate.years_of_experience:.1f}y)")

        if features.consulting_only_flag:
            concerns.append("consulting/services-only career (no product company)")

        if features.engagement_score < 0.3:
            concerns.append("low platform engagement/responsiveness")

        if features.notice_period_days > 90:
            concerns.append(f"long notice period ({features.notice_period_days}d)")

        if not features.location_match and not features.willing_to_relocate:
            concerns.append(f"outside preferred location ({candidate.country})")

        if features.anti_skill_penalty > 0.3:
            concerns.append("primary skills are in wrong domain (CV/speech/robotics)")

        if features.career_consistency_score < 0.4:
            concerns.append("career description inconsistencies detected")

        if features.skill_inflation_score > 0.3:
            concerns.append("skill-endorsement inconsistency detected")

        return concerns

    def _get_relevant_skills(self, candidate: Candidate) -> List[str]:
        """Get the candidate's skills that are relevant to the JD."""
        jd = self.settings.jd
        required = {s.lower() for s in jd.required_skills}
        preferred = {s.lower() for s in jd.preferred_skills}

        relevant = []
        for skill in candidate.skills:
            name = skill.get("name", "")
            if name.lower() in required or name.lower() in preferred:
                relevant.append(name)

        return relevant[:5]  # limit for readability
