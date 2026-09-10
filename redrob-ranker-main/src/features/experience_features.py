"""
Experience Feature Family.

Models the experience fit:
- Is candidate in the right experience band (5-9 years)?
- Domain experience (months in AI/ML/Search/NLP)
- Recency and relevance of experience
"""
from typing import Dict, List

from src.config.settings import Settings, get_settings


class ExperienceFeatureExtractor:
    """Extract experience-related features."""

    def __init__(self, settings: Settings = None):
        self.settings = settings or get_settings()
        self.jd = self.settings.jd

    def extract(self, profile: Dict, career_history: List[Dict]) -> Dict[str, float]:
        """Extract experience features."""
        features = {}
        yoe = profile.get("years_of_experience", 0.0)

        # 1. Experience fit score (bell curve centered on JD range)
        features["experience_fit_score"] = self._compute_experience_fit(yoe)

        # 2. Years of experience (raw)
        features["years_of_experience"] = yoe

        # 3. In range flag
        min_exp, max_exp = self.jd.experience_range
        features["experience_in_range"] = float(min_exp <= yoe <= max_exp)

        # 4. Domain experience (months in relevant roles)
        features["domain_experience_months"] = self._compute_domain_experience(
            career_history
        )

        return features

    def _compute_experience_fit(self, yoe: float) -> float:
        """
        Bell-curve scoring around the JD's 5-9 year range.
        Peak at 6-8 years (ideal), graceful decay outside.
        """
        min_exp, max_exp = self.jd.experience_range
        ideal_center = (min_exp + max_exp) / 2  # 7 years

        if min_exp <= yoe <= max_exp:
            # Perfect range
            return 1.0
        elif yoe < min_exp:
            # Below range — penalize more harshly below hard minimum
            if yoe < self.jd.experience_hard_min:
                return 0.1
            distance = min_exp - yoe
            return max(1.0 - (distance / 3.0) * 0.5, 0.3)
        else:
            # Above range — gentler decay but still meaningful
            distance = yoe - max_exp
            if distance <= 2:
                return 0.85  # 9-11 years: slight penalty
            elif distance <= 4:
                return 0.65  # 11-13 years: moderate
            elif distance <= 6:
                return 0.45  # 13-15 years: significant
            else:
                return 0.30  # 15+ years: heavy (likely over-qualified)

    def _compute_domain_experience(self, career: List[Dict]) -> int:
        """
        Total months spent in AI/ML/Search/NLP relevant roles.
        Looks at both titles and descriptions.
        """
        relevant_keywords = [
            "machine learning", "ml", "ai", "artificial intelligence",
            "deep learning", "nlp", "natural language", "search",
            "ranking", "recommendation", "retrieval", "embedding",
            "data science", "neural", "model", "inference",
            "computer science", "software engineer"
        ]

        total_relevant_months = 0
        for job in career:
            title = job.get("title", "").lower()
            desc = job.get("description", "").lower()
            duration = job.get("duration_months", 0)

            is_relevant = any(
                kw in title or kw in desc for kw in relevant_keywords
            )
            if is_relevant:
                total_relevant_months += duration

        return total_relevant_months
