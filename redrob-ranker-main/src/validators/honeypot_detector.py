"""
Honeypot Detection Engine.

Identifies candidates with subtly impossible profiles:
- Impossible tenure (more YoE at company than company's age)
- Expert proficiency in many skills with very low total experience
- Future dates
- Contradictory career timelines
- Keyword stuffing patterns (many advanced/expert skills, zero endorsements)
- Title-experience mismatch
"""
from datetime import date, datetime
from typing import Dict, List, Tuple

from src.config.settings import Settings, get_settings
from src.core.types import Candidate


class HoneypotDetector:
    """Detects honeypot candidates with impossible or suspicious profiles."""

    def __init__(self, settings: Settings = None):
        self.settings = settings or get_settings()
        self.cfg = self.settings.honeypot

    def detect(self, candidate: Candidate) -> Tuple[bool, List[str], float]:
        """
        Analyze a candidate for honeypot indicators.

        Returns:
            (is_honeypot, reasons, trust_penalty)
            trust_penalty is 0.0 for clean profiles, up to -1.0 for definite honeypots
        """
        reasons = []
        penalty = 0.0

        # Check 1: Skills with impossible proficiency vs experience
        penalty += self._check_skill_inflation(candidate, reasons)

        # Check 2: Career timeline impossibilities
        penalty += self._check_career_timeline(candidate, reasons)

        # Check 3: Future dates
        penalty += self._check_future_dates(candidate, reasons)

        # Check 4: Experience vs skill duration mismatch
        penalty += self._check_experience_skill_mismatch(candidate, reasons)

        # Check 5: Keyword stuffing pattern
        penalty += self._check_keyword_stuffing(candidate, reasons)

        # Check 6: Title-description incoherence
        penalty += self._check_title_description_mismatch(candidate, reasons)

        is_honeypot = penalty <= -0.8  # threshold for honeypot classification (stricter)
        return is_honeypot, reasons, max(penalty, -1.0)

    def _check_skill_inflation(self, candidate: Candidate, reasons: List[str]) -> float:
        """Check for impossible skill proficiency levels given experience."""
        penalty = 0.0
        skills = candidate.skills

        if not skills:
            return 0.0

        expert_advanced_count = sum(
            1 for s in skills
            if s.get("proficiency") in ("expert", "advanced")
        )
        total_skills = len(skills)

        # Many expert/advanced skills relative to total
        # But only penalize if experience is LOW — a 7-year senior SHOULD have many advanced skills
        if total_skills > 0:
            inflation_ratio = expert_advanced_count / total_skills
            # Only penalize if: high inflation AND low experience AND many skills
            if (inflation_ratio > self.cfg.skill_inflation_threshold
                    and total_skills >= 10
                    and candidate.years_of_experience < 4.0):
                penalty -= 0.3
                reasons.append(
                    f"Skill inflation: {expert_advanced_count}/{total_skills} "
                    f"skills at expert/advanced level with only "
                    f"{candidate.years_of_experience:.1f}y experience"
                )

        # Expert in many skills with very low total experience
        if (candidate.years_of_experience < self.cfg.min_experience_for_expert_count
                and expert_advanced_count > self.cfg.max_expert_skills_low_experience):
            penalty -= 0.4
            reasons.append(
                f"Expert in {expert_advanced_count} skills with only "
                f"{candidate.years_of_experience:.1f} years experience"
            )

        # Skills with zero duration but high proficiency
        zero_duration_expert = sum(
            1 for s in skills
            if s.get("proficiency") in ("expert", "advanced")
            and s.get("duration_months", 0) == 0
        )
        if zero_duration_expert > self.cfg.max_skills_with_zero_duration:
            penalty -= 0.3
            reasons.append(
                f"{zero_duration_expert} expert/advanced skills with 0 months duration"
            )

        return penalty

    def _check_career_timeline(self, candidate: Candidate, reasons: List[str]) -> float:
        """Check for impossible career timelines."""
        penalty = 0.0
        career = candidate.career_history

        if len(career) < 2:
            return 0.0

        # Check: total duration_months vastly exceeds actual time span
        # This is the most reliable signal — overlaps can be legitimate (two part-time roles)
        total_claimed_months = sum(
            j.get("duration_months", 0) for j in career
        )
        if candidate.years_of_experience > 0:
            actual_months = candidate.years_of_experience * 12
            # Only penalize if claimed months are WAY more than actual (>2x)
            if total_claimed_months > actual_months * 2.0 and total_claimed_months > 100:
                penalty -= 0.3
                reasons.append(
                    f"Career months ({total_claimed_months}) exceed "
                    f"actual experience ({actual_months:.0f} months) by >2x"
                )

        return penalty

    def _check_future_dates(self, candidate: Candidate, reasons: List[str]) -> float:
        """Check for dates in the future that shouldn't be."""
        penalty = 0.0
        today = date(2026, 6, 27)  # competition reference date
        tolerance = self.cfg.future_date_tolerance_days

        signals = candidate.redrob_signals
        for date_field in ["signup_date", "last_active_date"]:
            val = signals.get(date_field)
            if val:
                try:
                    d = datetime.strptime(str(val), "%Y-%m-%d").date()
                    if (d - today).days > tolerance:
                        penalty -= 0.3
                        reasons.append(f"Future date in {date_field}: {val}")
                except (ValueError, TypeError):
                    continue

        return penalty

    def _check_experience_skill_mismatch(self, candidate: Candidate, reasons: List[str]) -> float:
        """
        Check if total skill duration vastly exceeds career duration.
        A candidate with 3 years experience claiming 60+ months in 10 skills is suspicious.
        But a candidate with 7 years can legitimately have high total skill months
        (multiple skills used concurrently).
        """
        penalty = 0.0
        total_skill_months = sum(
            s.get("duration_months", 0) for s in candidate.skills
        )
        experience_months = max(candidate.years_of_experience * 12, 1)
        ratio = total_skill_months / experience_months

        # Only flag if ratio is extreme AND experience is low
        if ratio > 12 and candidate.years_of_experience < 4 and len(candidate.skills) > 12:
            penalty -= 0.2
            reasons.append(
                f"Total skill duration ({total_skill_months}mo) is "
                f"{ratio:.1f}x actual experience ({experience_months:.0f}mo) "
                f"with only {candidate.years_of_experience:.1f}y total experience"
            )

        return penalty

    def _check_keyword_stuffing(self, candidate: Candidate, reasons: List[str]) -> float:
        """
        Detect keyword stuffing: many AI/ML skills with no supporting career evidence.
        """
        penalty = 0.0
        ai_keywords = {
            "NLP", "LLM", "RAG", "transformers", "BERT", "GPT",
            "fine-tuning", "embeddings", "vector database", "ML",
            "deep learning", "neural networks", "PyTorch", "TensorFlow",
            "computer vision", "speech recognition", "GANs",
            "reinforcement learning", "recommendation systems",
            "Fine-tuning LLMs", "LoRA", "Image Classification",
            "Object Detection", "TTS", "Speech Recognition"
        }

        skill_names = {s.get("name", "").lower() for s in candidate.skills}
        ai_skill_count = sum(
            1 for s in candidate.skills
            if s.get("name", "") in ai_keywords or s.get("name", "").lower() in {k.lower() for k in ai_keywords}
        )

        # Check if career history mentions AI/ML work
        career_text = " ".join(
            j.get("description", "") for j in candidate.career_history
        ).lower()

        ai_career_keywords = [
            "machine learning", "ml", "ai", "deep learning", "neural",
            "nlp", "embedding", "model", "training", "inference",
            "retrieval", "ranking", "recommendation", "search"
        ]
        career_ai_mentions = sum(
            1 for kw in ai_career_keywords if kw in career_text
        )

        # Many AI skills but no AI in career history = suspicious
        if ai_skill_count >= 5 and career_ai_mentions <= 1:
            # Check title too
            title_lower = candidate.current_title.lower()
            ai_titles = ["engineer", "developer", "scientist", "ml", "ai", "data"]
            title_has_ai = any(t in title_lower for t in ai_titles)

            if not title_has_ai:
                penalty -= 0.3
                reasons.append(
                    f"Keyword stuffing: {ai_skill_count} AI skills but "
                    f"title is '{candidate.current_title}' with no AI career evidence"
                )

        return penalty

    def _check_title_description_mismatch(self, candidate: Candidate, reasons: List[str]) -> float:
        """
        Check if the career descriptions don't match the titles.
        Honeypots often have mismatched title/description pairs.
        """
        penalty = 0.0

        for job in candidate.career_history:
            title = job.get("title", "").lower()
            desc = job.get("description", "").lower()

            if not desc or not title:
                continue

            # Major mismatches
            mismatches = [
                (["accountant", "accounting"], ["machine learning", "deep learning", "neural"]),
                (["hr manager", "human resources"], ["software engineer", "coding", "python", "ml"]),
                (["marketing manager"], ["mechanical engineering", "CAD", "solidworks"]),
                (["customer support"], ["data pipeline", "spark", "airflow"]),
                (["content writer"], ["kubernetes", "docker", "microservices"]),
                (["sales executive"], ["neural network", "pytorch", "tensorflow"]),
                (["graphic designer"], ["distributed systems", "backend", "api"]),
            ]

            for title_keywords, desc_keywords in mismatches:
                title_match = any(tk in title for tk in title_keywords)
                desc_match = any(dk in desc for dk in desc_keywords)
                if title_match and desc_match:
                    # This is suspicious but could be a career transition
                    # Only light penalty — some people genuinely transition
                    penalty -= 0.1
                    reasons.append(
                        f"Title-description mismatch: '{job.get('title')}' "
                        f"but description mentions different domain"
                    )
                    break  # one per job is enough

        return min(penalty, 0.0)  # cap at 0
