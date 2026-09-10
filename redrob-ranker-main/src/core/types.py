"""
Core type definitions for the ranking system.
These are the canonical data structures used throughout the pipeline.
"""
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional


class RelevanceTier(Enum):
    """Ground truth relevance tiers (for self-supervised training)."""
    TIER_0_HONEYPOT = 0
    TIER_1_IRRELEVANT = 1
    TIER_2_WEAK = 2
    TIER_3_MODERATE = 3
    TIER_4_STRONG = 4
    TIER_5_EXCELLENT = 5


class CareerMove(Enum):
    """Types of career transitions."""
    PROMOTION = "promotion"
    LATERAL = "lateral"
    REGRESSION = "regression"
    DOMAIN_SHIFT = "domain_shift"
    STARTUP_JOIN = "startup_join"
    ENTERPRISE_JOIN = "enterprise_join"


@dataclass
class Candidate:
    """Parsed and validated candidate record."""
    candidate_id: str
    # Profile
    headline: str = ""
    summary: str = ""
    location: str = ""
    country: str = ""
    years_of_experience: float = 0.0
    current_title: str = ""
    current_company: str = ""
    current_company_size: str = ""
    current_industry: str = ""
    # Structured
    career_history: List[Dict[str, Any]] = field(default_factory=list)
    education: List[Dict[str, Any]] = field(default_factory=list)
    skills: List[Dict[str, Any]] = field(default_factory=list)
    certifications: List[Dict[str, Any]] = field(default_factory=list)
    languages: List[Dict[str, Any]] = field(default_factory=list)
    redrob_signals: Dict[str, Any] = field(default_factory=dict)
    # Computed
    is_honeypot: bool = False
    honeypot_reasons: List[str] = field(default_factory=list)
    trust_score: float = 1.0


@dataclass
class FeatureVector:
    """Complete feature vector for a candidate relative to a JD."""
    candidate_id: str
    # Skills features
    skill_match_ratio: float = 0.0
    skill_semantic_score: float = 0.0
    skill_proficiency_score: float = 0.0
    skill_endorsement_score: float = 0.0
    skill_assessment_avg: float = 0.0
    skill_depth_score: float = 0.0
    anti_skill_penalty: float = 0.0
    required_skill_count: int = 0
    preferred_skill_count: int = 0
    total_skill_count: int = 0
    # Career features
    title_relevance_score: float = 0.0
    career_trajectory_score: float = 0.0
    product_company_ratio: float = 0.0
    consulting_only_flag: bool = False
    career_stability_score: float = 0.0
    avg_tenure_months: float = 0.0
    career_recency_score: float = 0.0
    total_roles: int = 0
    promotion_count: int = 0
    # Experience features
    experience_fit_score: float = 0.0
    years_of_experience: float = 0.0
    experience_in_range: bool = False
    domain_experience_months: int = 0
    # Education features
    education_tier_score: float = 0.0
    education_field_relevance: float = 0.0
    highest_degree_level: int = 0
    # Behavioral features
    engagement_score: float = 0.0
    availability_score: float = 0.0
    platform_trust_score: float = 0.0
    recruiter_interest_score: float = 0.0
    response_rate: float = 0.0
    notice_period_days: int = 0
    open_to_work: bool = False
    last_active_recency_days: int = 0
    # Trust / Honeypot features
    trust_score: float = 1.0
    profile_completeness: float = 0.0
    verification_score: float = 0.0
    skill_inflation_score: float = 0.0
    career_consistency_score: float = 0.0
    # Location features
    location_match: bool = False
    willing_to_relocate: bool = False
    preferred_work_mode_match: bool = False
    # Retrieval scores
    bm25_score: float = 0.0
    dense_score_career: float = 0.0
    dense_score_skills: float = 0.0
    dense_score_responsibilities: float = 0.0
    rrf_score: float = 0.0

    def to_array(self) -> List[float]:
        """Convert to flat feature array for LTR model."""
        return [
            self.skill_match_ratio,
            self.skill_semantic_score,
            self.skill_proficiency_score,
            self.skill_endorsement_score,
            self.skill_assessment_avg,
            self.skill_depth_score,
            self.anti_skill_penalty,
            float(self.required_skill_count),
            float(self.preferred_skill_count),
            self.title_relevance_score,
            self.career_trajectory_score,
            self.product_company_ratio,
            float(self.consulting_only_flag),
            self.career_stability_score,
            self.avg_tenure_months,
            self.career_recency_score,
            float(self.promotion_count),
            self.experience_fit_score,
            self.years_of_experience,
            float(self.experience_in_range),
            float(self.domain_experience_months),
            self.education_tier_score,
            self.education_field_relevance,
            float(self.highest_degree_level),
            self.engagement_score,
            self.availability_score,
            self.platform_trust_score,
            self.recruiter_interest_score,
            self.response_rate,
            float(self.notice_period_days),
            float(self.open_to_work),
            float(self.last_active_recency_days),
            self.trust_score,
            self.profile_completeness,
            self.verification_score,
            self.skill_inflation_score,
            self.career_consistency_score,
            float(self.location_match),
            float(self.willing_to_relocate),
            float(self.preferred_work_mode_match),
            self.bm25_score,
            self.dense_score_career,
            self.dense_score_skills,
            self.dense_score_responsibilities,
            self.rrf_score,
        ]

    @staticmethod
    def feature_names() -> List[str]:
        """Return ordered feature names matching to_array()."""
        return [
            "skill_match_ratio",
            "skill_semantic_score",
            "skill_proficiency_score",
            "skill_endorsement_score",
            "skill_assessment_avg",
            "skill_depth_score",
            "anti_skill_penalty",
            "required_skill_count",
            "preferred_skill_count",
            "title_relevance_score",
            "career_trajectory_score",
            "product_company_ratio",
            "consulting_only_flag",
            "career_stability_score",
            "avg_tenure_months",
            "career_recency_score",
            "promotion_count",
            "experience_fit_score",
            "years_of_experience",
            "experience_in_range",
            "domain_experience_months",
            "education_tier_score",
            "education_field_relevance",
            "highest_degree_level",
            "engagement_score",
            "availability_score",
            "platform_trust_score",
            "recruiter_interest_score",
            "response_rate",
            "notice_period_days",
            "open_to_work",
            "last_active_recency_days",
            "trust_score",
            "profile_completeness",
            "verification_score",
            "skill_inflation_score",
            "career_consistency_score",
            "location_match",
            "willing_to_relocate",
            "preferred_work_mode_match",
            "bm25_score",
            "dense_score_career",
            "dense_score_skills",
            "dense_score_responsibilities",
            "rrf_score",
        ]


@dataclass
class RankedCandidate:
    """Final output: a ranked candidate with score and reasoning."""
    candidate_id: str
    rank: int
    score: float
    reasoning: str
    # Internal (not in output)
    feature_contributions: Dict[str, float] = field(default_factory=dict)
    top_features: List[str] = field(default_factory=list)
