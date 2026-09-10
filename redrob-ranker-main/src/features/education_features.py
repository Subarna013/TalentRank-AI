"""
Education Feature Family.

Light weight (5% of total score) — education matters less for this role
than demonstrated production experience.
"""
from typing import Dict, List

from src.config.settings import Settings, get_settings


class EducationFeatureExtractor:
    """Extract education-related features."""

    DEGREE_LEVELS = {
        "ph.d": 5, "phd": 5,
        "m.tech": 4, "mtech": 4, "m.e.": 4, "me": 4,
        "m.sc": 3, "msc": 3, "m.s.": 3, "ms": 3, "mba": 3,
        "b.tech": 2, "btech": 2, "b.e.": 2, "be": 2,
        "b.sc": 2, "bsc": 2, "b.s.": 2, "bs": 2, "bca": 2,
        "diploma": 1,
    }

    RELEVANT_FIELDS = {
        "computer science", "computer engineering", "artificial intelligence",
        "machine learning", "data science", "information technology",
        "software engineering", "electrical engineering", "electronics",
        "mathematics", "statistics", "applied mathematics",
        "computational linguistics", "cognitive science",
    }

    TIER_SCORES = {
        "tier_1": 1.0,
        "tier_2": 0.7,
        "tier_3": 0.4,
        "tier_4": 0.2,
        "unknown": 0.3,
    }

    def __init__(self, settings: Settings = None):
        self.settings = settings or get_settings()

    def extract(self, education: List[Dict]) -> Dict[str, float]:
        """Extract education features."""
        features = {}

        if not education:
            features["education_tier_score"] = 0.0
            features["education_field_relevance"] = 0.0
            features["highest_degree_level"] = 0
            return features

        # 1. Best institution tier
        best_tier = max(
            self.TIER_SCORES.get(e.get("tier", "unknown"), 0.2)
            for e in education
        )
        features["education_tier_score"] = best_tier

        # 2. Field relevance (is the degree in a relevant field?)
        best_field_score = 0.0
        for edu in education:
            field = edu.get("field_of_study", "").lower()
            if field in self.RELEVANT_FIELDS:
                best_field_score = 1.0
                break
            # Partial matches
            for relevant in self.RELEVANT_FIELDS:
                if relevant in field or field in relevant:
                    best_field_score = max(best_field_score, 0.7)
        features["education_field_relevance"] = best_field_score

        # 3. Highest degree level
        highest = 0
        for edu in education:
            degree = edu.get("degree", "").lower()
            for degree_key, level in self.DEGREE_LEVELS.items():
                if degree_key in degree:
                    highest = max(highest, level)
                    break
        features["highest_degree_level"] = highest

        return features
