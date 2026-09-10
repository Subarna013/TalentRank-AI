"""
Career Feature Family.

Extracts career trajectory, stability, and relevance features:
- Title relevance to JD
- Career trajectory (promotions vs regressions)
- Product company vs services ratio
- Consulting-only flag
- Tenure stability
- Recency of relevant work
- Career graph modeling
"""
from datetime import datetime, date
from typing import Dict, List, Tuple

from src.config.settings import Settings, get_settings


class CareerFeatureExtractor:
    """Extract career-related features for a candidate."""

    # Title relevance tiers
    TITLE_TIER_1 = {  # Direct match
        "ai engineer", "ml engineer", "machine learning engineer",
        "senior ai engineer", "senior ml engineer", "applied ml engineer",
        "nlp engineer", "search engineer", "ranking engineer",
        "applied scientist", "research engineer", "senior applied scientist",
        "recommendation systems engineer", "ai research engineer",
        "lead ai engineer", "staff ml engineer",
    }
    TITLE_TIER_2 = {  # Strong adjacent
        "data scientist", "senior data scientist", "ml ops engineer",
        "backend engineer", "senior software engineer", "staff engineer",
        "principal engineer", "full stack engineer", "platform engineer",
        "junior ml engineer", "junior ai engineer",
        "senior software engineer (ml)", "computer vision engineer",
    }
    TITLE_TIER_3 = {  # Weak adjacent
        "data engineer", "analytics engineer", "software engineer",
        "developer", "tech lead", "engineering manager",
    }
    TITLE_IRRELEVANT = {  # Non-technical
        "hr manager", "marketing manager", "sales executive",
        "accountant", "graphic designer", "content writer",
        "operations manager", "customer support", "business analyst",
        "project manager", "product manager",
    }

    def __init__(self, settings: Settings = None):
        self.settings = settings or get_settings()
        self.jd = self.settings.jd

    def extract(self, career_history: List[Dict], profile: Dict) -> Dict[str, float]:
        """Extract all career features."""
        features = {}

        # 1. Current title relevance
        current_title = profile.get("current_title", "").lower()
        features["title_relevance_score"] = self._score_title(current_title)

        # 2. Career trajectory
        features["career_trajectory_score"] = self._compute_trajectory(career_history)

        # 3. Product vs services company ratio
        features["product_company_ratio"] = self._compute_product_ratio(career_history)

        # 4. Consulting-only flag
        features["consulting_only_flag"] = self._is_consulting_only(career_history)

        # 5. Career stability
        features["career_stability_score"] = self._compute_stability(career_history)

        # 6. Average tenure
        features["avg_tenure_months"] = self._compute_avg_tenure(career_history)

        # 7. Recency of relevant work
        features["career_recency_score"] = self._compute_recency(career_history)

        # 8. Total roles count
        features["total_roles"] = len(career_history)

        # 9. Promotion count
        features["promotion_count"] = self._count_promotions(career_history)

        # 10. Career consistency (do titles/descriptions match?)
        features["career_consistency_score"] = self._compute_consistency(career_history)

        return features

    def _score_title(self, title: str) -> float:
        """Score how relevant the current title is to the JD."""
        title_lower = title.lower().strip()

        # Direct match
        if title_lower in self.TITLE_TIER_1:
            return 1.0
        # Check partial matches
        for t in self.TITLE_TIER_1:
            if t in title_lower or title_lower in t:
                return 0.95

        if title_lower in self.TITLE_TIER_2:
            return 0.7
        for t in self.TITLE_TIER_2:
            if t in title_lower or title_lower in t:
                return 0.65

        if title_lower in self.TITLE_TIER_3:
            return 0.4
        for t in self.TITLE_TIER_3:
            if t in title_lower or title_lower in t:
                return 0.35

        if title_lower in self.TITLE_IRRELEVANT:
            return 0.05
        for t in self.TITLE_IRRELEVANT:
            if t in title_lower:
                return 0.05

        # Unknown title — give benefit of doubt
        return 0.2

    def _compute_trajectory(self, career: List[Dict]) -> float:
        """
        Model career trajectory as a graph.
        Promotions = positive, lateral = neutral, regressions = slight negative.
        """
        if len(career) < 2:
            return 0.5  # neutral

        promotions = 0
        laterals = 0
        regressions = 0

        for i in range(len(career) - 1):
            current_title = career[i].get("title", "").lower()
            prev_title = career[i + 1].get("title", "").lower()

            current_score = self._title_seniority(current_title)
            prev_score = self._title_seniority(prev_title)

            if current_score > prev_score:
                promotions += 1
            elif current_score == prev_score:
                laterals += 1
            else:
                regressions += 1

        total_moves = promotions + laterals + regressions
        if total_moves == 0:
            return 0.5

        # Trajectory score: promotions are good, regressions are concerning
        score = (promotions * 1.0 + laterals * 0.5 - regressions * 0.3) / total_moves
        return max(min(score, 1.0), 0.0)

    def _title_seniority(self, title: str) -> int:
        """Map title to seniority level."""
        title_lower = title.lower()
        seniority_keywords = {
            "intern": 1, "junior": 2, "associate": 3,
            "": 4,  # default mid-level
            "senior": 5, "lead": 6, "staff": 7,
            "principal": 8, "director": 9, "vp": 10,
            "head": 9, "chief": 10, "cto": 10, "ceo": 10,
        }
        for keyword, level in sorted(seniority_keywords.items(), key=lambda x: -x[1]):
            if keyword and keyword in title_lower:
                return level
        return 4  # mid-level default

    def _compute_product_ratio(self, career: List[Dict]) -> float:
        """
        What fraction of career was at product companies vs services?
        The JD explicitly prefers product company experience.
        """
        if not career:
            return 0.5

        services_companies = {c.lower() for c in self.jd.consulting_companies}
        services_industries = {"it services", "consulting", "staffing"}

        total_months = 0
        product_months = 0

        for job in career:
            duration = job.get("duration_months", 0)
            company = job.get("company", "").lower()
            industry = job.get("industry", "").lower()

            total_months += duration

            is_services = (
                company in services_companies or
                industry in services_industries
            )
            if not is_services:
                product_months += duration

        if total_months == 0:
            return 0.5
        return product_months / total_months

    def _is_consulting_only(self, career: List[Dict]) -> float:
        """Check if candidate has ONLY consulting/services experience."""
        services_companies = {c.lower() for c in self.jd.consulting_companies}
        services_industries = {"it services", "consulting", "staffing"}

        for job in career:
            company = job.get("company", "").lower()
            industry = job.get("industry", "").lower()
            if company not in services_companies and industry not in services_industries:
                return 0.0  # has at least some non-consulting experience
        return 1.0  # all consulting

    def _compute_stability(self, career: List[Dict]) -> float:
        """
        Career stability score.
        Penalizes: very short tenures (< 12 months), too many job changes.
        The JD says they don't want title-chasers switching every 1.5 years.
        """
        if not career:
            return 0.5

        short_stints = sum(
            1 for j in career if j.get("duration_months", 0) < 12
        )
        total_jobs = len(career)

        # Short stint ratio (lower is better)
        if total_jobs == 0:
            return 0.5

        short_ratio = short_stints / total_jobs
        # Invert: less short stints = higher stability
        return max(1.0 - short_ratio, 0.0)

    def _compute_avg_tenure(self, career: List[Dict]) -> float:
        """Average tenure in months across career."""
        if not career:
            return 0.0
        tenures = [j.get("duration_months", 0) for j in career]
        return sum(tenures) / len(tenures)

    def _compute_recency(self, career: List[Dict]) -> float:
        """
        How recent is the candidate's relevant (AI/ML/tech) work?
        More recent relevant work = higher score.
        """
        if not career:
            return 0.0

        reference_date = date(2026, 6, 27)
        best_recency = 0.0

        for job in career:
            title = job.get("title", "").lower()
            desc = job.get("description", "").lower()

            # Is this role relevant?
            relevant_keywords = [
                "ml", "ai", "machine learning", "data science",
                "search", "ranking", "retrieval", "nlp", "embedding",
                "recommendation", "engineer", "developer", "backend"
            ]
            is_relevant = any(kw in title or kw in desc for kw in relevant_keywords)

            if is_relevant:
                end_date_str = job.get("end_date")
                if job.get("is_current", False) or end_date_str is None:
                    best_recency = 1.0  # currently in relevant role
                    break
                else:
                    try:
                        end_date = datetime.strptime(str(end_date_str), "%Y-%m-%d").date()
                        months_ago = (reference_date - end_date).days / 30
                        recency = max(1.0 - (months_ago / 24), 0.0)  # decay over 2 years
                        best_recency = max(best_recency, recency)
                    except (ValueError, TypeError):
                        continue

        return best_recency

    def _count_promotions(self, career: List[Dict]) -> int:
        """Count visible promotions (same company, higher title)."""
        promotions = 0
        for i in range(len(career) - 1):
            if career[i].get("company") == career[i + 1].get("company"):
                current_seniority = self._title_seniority(career[i].get("title", ""))
                prev_seniority = self._title_seniority(career[i + 1].get("title", ""))
                if current_seniority > prev_seniority:
                    promotions += 1
        return promotions

    def _compute_consistency(self, career: List[Dict]) -> float:
        """
        Check career consistency — do the descriptions match the titles?
        Honeypots often have random descriptions assigned to titles.
        """
        if not career:
            return 0.5

        consistent_count = 0
        total_checked = 0

        for job in career:
            title = job.get("title", "").lower()
            desc = job.get("description", "").lower()

            if not desc or not title:
                continue

            total_checked += 1

            # Simple heuristic: does the description mention anything
            # related to the title's domain?
            domain_keywords = {
                "engineer": ["code", "build", "develop", "system", "technical",
                           "implement", "architecture", "deploy", "pipeline"],
                "manager": ["team", "manage", "lead", "kpi", "strategy",
                          "stakeholder", "process", "operations"],
                "analyst": ["analysis", "data", "report", "insight", "model",
                          "research", "diagnostic", "consulting"],
                "designer": ["design", "creative", "visual", "brand", "ui",
                           "ux", "adobe", "figma", "layout"],
                "writer": ["content", "write", "editorial", "article", "seo",
                         "blog", "copy", "publication"],
                "accountant": ["accounting", "financial", "audit", "tax",
                             "compliance", "gaap", "budget", "ledger"],
                "sales": ["sales", "revenue", "client", "deal", "pipeline",
                        "quota", "business development"],
                "support": ["support", "ticket", "customer", "helpdesk",
                          "escalation", "resolution"],
            }

            matched = False
            for title_keyword, desc_keywords in domain_keywords.items():
                if title_keyword in title:
                    if any(dk in desc for dk in desc_keywords):
                        matched = True
                        consistent_count += 1
                    break

            if not matched:
                # If we didn't find a matching pattern, give neutral score
                consistent_count += 0.5

        if total_checked == 0:
            return 0.5
        return consistent_count / total_checked
