"""
Location Feature Family.

Checks location/country match and work mode compatibility.
"""
from typing import Dict

from src.config.settings import Settings, get_settings


class LocationFeatureExtractor:
    """Extract location-related features."""

    def __init__(self, settings: Settings = None):
        self.settings = settings or get_settings()
        self.jd = self.settings.jd

    def extract(self, profile: Dict, signals: Dict) -> Dict[str, float]:
        """Extract location features."""
        features = {}

        location = profile.get("location", "").lower()
        country = profile.get("country", "").lower()

        # 1. Location match
        location_match = False
        for preferred in self.jd.preferred_locations:
            if preferred.lower() in location:
                location_match = True
                break

        # Country match
        country_match = any(
            c.lower() == country for c in self.jd.preferred_countries
        )

        features["location_match"] = float(location_match or country_match)

        # 2. Willing to relocate (relevant if not in location)
        features["willing_to_relocate"] = float(
            signals.get("willing_to_relocate", False)
        )

        # 3. Work mode compatibility
        preferred_mode = signals.get("preferred_work_mode", "onsite")
        compatible_modes = {"hybrid", "onsite", "flexible"}
        features["preferred_work_mode_match"] = float(
            preferred_mode in compatible_modes
        )

        # 4. Salary alignment (Series A startup in India: ~20-60 LPA range)
        salary = signals.get("expected_salary_range_inr_lpa", {})
        salary_min = salary.get("min", 0)
        salary_max = salary.get("max", 0)
        # Rough alignment: 15-65 LPA is reasonable for this role
        if salary_max <= 65 and salary_min >= 5:
            features["salary_alignment"] = 1.0
        elif salary_max <= 85:
            features["salary_alignment"] = 0.7
        elif salary_max > 100:
            features["salary_alignment"] = 0.4  # might be over-qualified/overpriced
        else:
            features["salary_alignment"] = 0.6

        return features
