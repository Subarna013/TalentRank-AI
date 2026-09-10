"""
Feature Registry — First-class citizen in the architecture.

Orchestrates all feature families, produces the complete feature vector
for a candidate, and supports:
- Feature importance tracking
- Feature toggling for ablation studies
- Reproducible feature computation
"""
from typing import Dict, List

from src.config.settings import Settings, get_settings
from src.core.types import Candidate, FeatureVector
from src.features.skills_features import SkillsFeatureExtractor
from src.features.career_features import CareerFeatureExtractor
from src.features.behavioral_features import BehavioralFeatureExtractor
from src.features.experience_features import ExperienceFeatureExtractor
from src.features.education_features import EducationFeatureExtractor
from src.features.location_features import LocationFeatureExtractor
from src.features.career_description_analyzer import CareerDescriptionAnalyzer
from src.features.advanced_skill_matcher import AdvancedSkillMatcher
from src.features.skill_canonicalizer import SkillCanonicalizer
from src.features.mutual_interest_scorer import MutualInterestScorer


class FeatureRegistry:
    """
    Central feature computation engine.
    Computes all features for a candidate and assembles the FeatureVector.
    """

    def __init__(self, settings: Settings = None):
        self.settings = settings or get_settings()

        # Initialize all feature extractors
        self.skills_extractor = SkillsFeatureExtractor(self.settings)
        self.career_extractor = CareerFeatureExtractor(self.settings)
        self.behavioral_extractor = BehavioralFeatureExtractor(self.settings)
        self.experience_extractor = ExperienceFeatureExtractor(self.settings)
        self.education_extractor = EducationFeatureExtractor(self.settings)
        self.location_extractor = LocationFeatureExtractor(self.settings)
        self.description_analyzer = CareerDescriptionAnalyzer()
        self.advanced_skill_matcher = AdvancedSkillMatcher()
        self.skill_canonicalizer = SkillCanonicalizer()
        self.mutual_interest_scorer = MutualInterestScorer(self.settings)

    def compute_features(self, candidate: Candidate) -> FeatureVector:
        """
        Compute the complete feature vector for a candidate.
        This is the single entry point for all feature computation.
        """
        fv = FeatureVector(candidate_id=candidate.candidate_id)

        # Skills features
        skills_feats = self.skills_extractor.extract(
            candidate.skills, candidate.redrob_signals
        )
        fv.skill_match_ratio = skills_feats.get("skill_match_ratio", 0.0)
        fv.skill_semantic_score = skills_feats.get("skill_semantic_score", 0.0)
        fv.skill_proficiency_score = skills_feats.get("skill_proficiency_score", 0.0)
        fv.skill_endorsement_score = skills_feats.get("skill_endorsement_score", 0.0)
        fv.skill_assessment_avg = skills_feats.get("skill_assessment_avg", 0.0)
        fv.skill_depth_score = skills_feats.get("skill_depth_score", 0.0)
        fv.anti_skill_penalty = skills_feats.get("anti_skill_penalty", 0.0)
        fv.required_skill_count = int(skills_feats.get("required_skill_count", 0))
        fv.preferred_skill_count = int(skills_feats.get("preferred_skill_count", 0))
        fv.total_skill_count = int(skills_feats.get("total_skill_count", 0))

        # Career features
        profile_dict = {
            "current_title": candidate.current_title,
            "current_company": candidate.current_company,
            "current_industry": candidate.current_industry,
        }
        career_feats = self.career_extractor.extract(
            candidate.career_history, profile_dict
        )
        fv.title_relevance_score = career_feats.get("title_relevance_score", 0.0)
        fv.career_trajectory_score = career_feats.get("career_trajectory_score", 0.0)
        fv.product_company_ratio = career_feats.get("product_company_ratio", 0.0)
        fv.consulting_only_flag = bool(career_feats.get("consulting_only_flag", False))
        fv.career_stability_score = career_feats.get("career_stability_score", 0.0)
        fv.avg_tenure_months = career_feats.get("avg_tenure_months", 0.0)
        fv.career_recency_score = career_feats.get("career_recency_score", 0.0)
        fv.total_roles = int(career_feats.get("total_roles", 0))
        fv.promotion_count = int(career_feats.get("promotion_count", 0))
        fv.career_consistency_score = career_feats.get("career_consistency_score", 0.5)

        # Experience features
        exp_profile = {
            "years_of_experience": candidate.years_of_experience,
        }
        exp_feats = self.experience_extractor.extract(
            exp_profile, candidate.career_history
        )
        fv.experience_fit_score = exp_feats.get("experience_fit_score", 0.0)
        fv.years_of_experience = exp_feats.get("years_of_experience", 0.0)
        fv.experience_in_range = bool(exp_feats.get("experience_in_range", False))
        fv.domain_experience_months = int(exp_feats.get("domain_experience_months", 0))

        # Education features
        edu_feats = self.education_extractor.extract(candidate.education)
        fv.education_tier_score = edu_feats.get("education_tier_score", 0.0)
        fv.education_field_relevance = edu_feats.get("education_field_relevance", 0.0)
        fv.highest_degree_level = int(edu_feats.get("highest_degree_level", 0))

        # Behavioral features
        behav_feats = self.behavioral_extractor.extract(candidate.redrob_signals)
        fv.engagement_score = behav_feats.get("engagement_score", 0.0)
        fv.availability_score = behav_feats.get("availability_score", 0.0)
        fv.platform_trust_score = behav_feats.get("platform_trust_score", 0.0)
        fv.recruiter_interest_score = behav_feats.get("recruiter_interest_score", 0.0)
        fv.response_rate = behav_feats.get("response_rate", 0.0)
        fv.notice_period_days = int(behav_feats.get("notice_period_days", 180))
        fv.open_to_work = bool(behav_feats.get("open_to_work", False))
        fv.last_active_recency_days = int(behav_feats.get("last_active_recency_days", 365))
        fv.profile_completeness = behav_feats.get("profile_completeness", 0.0)
        fv.verification_score = behav_feats.get("verification_score", 0.0)

        # Location features
        loc_profile = {
            "location": candidate.location,
            "country": candidate.country,
        }
        loc_feats = self.location_extractor.extract(
            loc_profile, candidate.redrob_signals
        )
        fv.location_match = bool(loc_feats.get("location_match", False))
        fv.willing_to_relocate = bool(loc_feats.get("willing_to_relocate", False))
        fv.preferred_work_mode_match = bool(loc_feats.get("preferred_work_mode_match", False))

        # Trust score (from honeypot detection — set externally)
        fv.trust_score = candidate.trust_score

        # Skill inflation (internal to trust)
        skill_trust = skills_feats.get("skill_trust_score", 1.0)
        fv.skill_inflation_score = 1.0 - skill_trust

        # Advanced: Career description analysis
        desc_feats = self.description_analyzer.analyze(candidate.career_history)
        # Store in auxiliary dict for composite scoring
        fv._desc_features = desc_feats

        # Advanced: Role readiness scoring
        career_text = " ".join(
            j.get("description", "") for j in candidate.career_history
        )
        readiness_feats = self.advanced_skill_matcher.compute_role_readiness(
            candidate.skills, career_text
        )
        fv._readiness_features = readiness_feats

        # Advanced: Canonical skill coverage
        canonical_feats = self.skill_canonicalizer.compute_jd_coverage(
            candidate.skills, career_text
        )
        fv._canonical_features = canonical_feats

        # Advanced: Mutual interest scoring (LinkedIn-style)
        profile_dict_mi = {
            "country": candidate.country,
            "location": candidate.location,
        }
        mutual_interest_feats = self.mutual_interest_scorer.compute(
            candidate.redrob_signals, profile_dict_mi
        )
        fv._mutual_interest_features = mutual_interest_feats

        return fv

    def compute_composite_score(self, fv: FeatureVector) -> float:
        """
        Production-grade composite scoring inspired by LinkedIn's Talent Search.

        Architecture (LinkedIn SIGIR 2018):
        - Quality Score: How relevant is this candidate to the JD?
        - Mutual Interest Score: Will the candidate respond and accept?
        - Final Score = Quality × Mutual Interest modifier

        Quality itself is multi-pass:
        - Pass 1: Canonical skill coverage (structured match)
        - Pass 2: Career evidence (semantic match from descriptions)
        - Pass 3: Role readiness (composite from advanced matcher)
        - Pass 4: Experience & trajectory fit
        """
        # ====== PASS 1: CANONICAL SKILL COVERAGE (Structured) ======
        canonical = getattr(fv, '_canonical_features', {})
        canonical_score = canonical.get("canonical_overall_score", 0.0)
        core_coverage = canonical.get("canonical_core_coverage", 0.0)

        # ====== PASS 2: CAREER EVIDENCE (Semantic) ======
        desc_feats = getattr(fv, '_desc_features', {})
        domain_evidence = desc_feats.get("domain_evidence_score", 0.0)
        production_evidence = desc_feats.get("production_evidence_score", 0.0)
        ic_work = desc_feats.get("ic_work_score", 0.0)
        domain_continuity = desc_feats.get("domain_continuity_score", 0.0)

        career_evidence = (
            0.35 * domain_evidence +
            0.25 * production_evidence +
            0.20 * ic_work +
            0.20 * domain_continuity
        )

        # ====== PASS 3: ROLE READINESS (Advanced matcher) ======
        readiness = getattr(fv, '_readiness_features', {})
        role_readiness = readiness.get("role_readiness_score", 0.0)
        required_coverage = readiness.get("required_coverage", 0.0)

        # ====== PASS 4: EXPERIENCE & TRAJECTORY ======
        experience_signal = (
            0.40 * fv.experience_fit_score +
            0.25 * fv.title_relevance_score +
            0.20 * fv.product_company_ratio +
            0.15 * fv.career_stability_score
        )

        # ====== QUALITY SCORE (Blend all passes) ======
        # Required coverage is a strong binary signal: does the candidate
        # cover ALL mandatory JD requirements?
        quality_score = (
            0.20 * canonical_score +        # Structured skill match
            0.10 * core_coverage +           # Bonus for covering core categories
            0.25 * career_evidence +         # What they actually built
            0.30 * role_readiness +          # Advanced requirement matching
            0.15 * experience_signal         # Experience & trajectory
        )

        # Anti-skill penalty (CV/speech/robotics focus when JD wants NLP/IR)
        if fv.anti_skill_penalty > 0.3:
            quality_score *= (1.0 - fv.anti_skill_penalty * 0.4)

        # Consulting-only hard penalty (JD explicitly warns)
        if fv.consulting_only_flag:
            quality_score *= 0.2

        # ====== MUTUAL INTEREST (LinkedIn-style) ======
        mi_feats = getattr(fv, '_mutual_interest_features', {})
        mutual_interest = mi_feats.get("mutual_interest_score", 0.5)

        # ====== FINAL SCORE = Quality × Mutual Interest modifier ======
        # Key insight: The competition asks "who are the best 100 fits for this JD"
        # NOT "who will definitely respond." A perfect-on-paper candidate who's
        # hard to reach is still a better RANKING choice than a mediocre candidate
        # who happens to be active. MI should modify, not dominate.
        #
        # LinkedIn uses MI as a strong signal because they optimize for recruiter
        # efficiency (don't show candidates who won't respond). But this competition
        # optimizes for RELEVANCE RANKING (NDCG), so quality dominates.
        final_score = quality_score * (0.70 + 0.30 * mutual_interest)

        # ====== MODIFIERS ======

        # Location: India required per JD
        if fv.location_match:
            final_score *= 1.05
        elif fv.willing_to_relocate:
            final_score *= 0.90
        else:
            # Non-India + won't relocate = very unlikely to hire
            final_score *= 0.55

        # Trust / Honeypot safety (from detector)
        if fv.trust_score >= 0.7:
            pass  # no penalty
        elif fv.trust_score >= 0.4:
            final_score *= (0.7 + 0.3 * fv.trust_score)
        else:
            final_score *= (0.2 + 0.5 * fv.trust_score)

        # Career consistency (catches honeypots with mismatched descriptions)
        if fv.career_consistency_score < 0.4:
            final_score *= (0.5 + 0.5 * fv.career_consistency_score)

        # Education (small bonus only for strong match)
        if fv.education_field_relevance > 0.7 and fv.education_tier_score > 0.6:
            final_score *= 1.03

        return max(min(final_score, 1.0), 0.0)
