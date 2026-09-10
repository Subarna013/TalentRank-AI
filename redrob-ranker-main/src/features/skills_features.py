"""
Skills Feature Family.

Computes skill-level features for candidate-JD matching:
- Semantic skill matching (not just keyword overlap)
- Proficiency depth scoring
- Endorsement signal
- Assessment score utilization
- Anti-skill penalty (wrong domain)
- Skill trust (endorsements × duration correlation)
"""
from typing import Dict, List, Set, Tuple

from src.config.settings import Settings, get_settings


class SkillsFeatureExtractor:
    """Extract skill-related features for a candidate against the JD."""

    def __init__(self, settings: Settings = None):
        self.settings = settings or get_settings()
        self.jd = self.settings.jd

        # Build normalized skill sets for matching
        self.required_skills_lower = {s.lower() for s in self.jd.required_skills}
        self.preferred_skills_lower = {s.lower() for s in self.jd.preferred_skills}
        self.anti_skills_lower = {s.lower() for s in self.jd.anti_skills}

        # Semantic skill groups (skills that indicate the same capability)
        self.skill_synonyms: Dict[str, Set[str]] = {
            "embeddings": {"embeddings", "sentence-transformers", "word2vec", "fasttext",
                          "bge", "e5", "openai embeddings", "vector representations"},
            "vector_db": {"faiss", "pinecone", "weaviate", "qdrant", "milvus",
                         "opensearch", "elasticsearch", "chroma", "vector database"},
            "nlp": {"nlp", "natural language processing", "text processing",
                   "spacy", "nltk", "huggingface", "transformers"},
            "ranking": {"ranking", "learning-to-rank", "ltr", "ndcg", "mrr",
                       "information retrieval", "search relevance", "bm25"},
            "llm": {"llm", "large language models", "gpt", "fine-tuning llms",
                   "lora", "qlora", "peft", "rlhf", "prompt engineering"},
            "python": {"python", "fastapi", "flask", "django", "pandas", "numpy"},
            "ml_ops": {"mlflow", "wandb", "weights & biases", "kubeflow",
                      "bentoml", "mlops", "model deployment"},
            "data_engineering": {"spark", "airflow", "kafka", "data pipelines",
                               "databricks", "dbt", "etl"},
        }

    def extract(self, candidate_skills: List[Dict], signals: Dict) -> Dict[str, float]:
        """
        Extract all skill features for a candidate.

        Args:
            candidate_skills: List of skill dicts from candidate profile
            signals: redrob_signals dict

        Returns:
            Dict of feature_name -> value
        """
        features = {}

        candidate_skill_names = [s.get("name", "").lower() for s in candidate_skills]
        candidate_skill_set = set(candidate_skill_names)

        # 1. Required skill match ratio
        required_matches = self._count_semantic_matches(
            candidate_skill_set, self.required_skills_lower
        )
        features["required_skill_count"] = required_matches
        features["skill_match_ratio"] = (
            required_matches / max(len(self.required_skills_lower), 1)
        )

        # 2. Preferred skill count
        preferred_matches = self._count_semantic_matches(
            candidate_skill_set, self.preferred_skills_lower
        )
        features["preferred_skill_count"] = preferred_matches

        # 3. Anti-skill penalty
        anti_matches = self._count_semantic_matches(
            candidate_skill_set, self.anti_skills_lower
        )
        # Penalty scales with how many anti-skills dominate
        anti_ratio = anti_matches / max(len(candidate_skills), 1)
        features["anti_skill_penalty"] = min(anti_ratio * 2.0, 1.0)

        # 4. Proficiency depth score
        features["skill_proficiency_score"] = self._compute_proficiency_score(
            candidate_skills
        )

        # 5. Endorsement signal
        features["skill_endorsement_score"] = self._compute_endorsement_score(
            candidate_skills
        )

        # 6. Assessment scores (from platform)
        features["skill_assessment_avg"] = self._compute_assessment_score(signals)

        # 7. Skill depth (duration-weighted relevance)
        features["skill_depth_score"] = self._compute_depth_score(candidate_skills)

        # 8. Semantic match score (using synonym groups)
        features["skill_semantic_score"] = self._compute_semantic_score(
            candidate_skill_set
        )

        # 9. Total skill count (for context)
        features["total_skill_count"] = len(candidate_skills)

        # 10. Skill trust signal
        features["skill_trust_score"] = self._compute_skill_trust(candidate_skills)

        return features

    def _count_semantic_matches(
        self, candidate_skills: Set[str], target_skills: Set[str]
    ) -> int:
        """Count how many target skills the candidate matches (including synonyms)."""
        matches = 0
        for target in target_skills:
            if target in candidate_skills:
                matches += 1
                continue
            # Check synonym groups
            for group_skills in self.skill_synonyms.values():
                if target in group_skills:
                    if candidate_skills & group_skills:
                        matches += 1
                        break
        return matches

    def _compute_proficiency_score(self, skills: List[Dict]) -> float:
        """
        Score proficiency of relevant skills.
        Expert=1.0, Advanced=0.75, Intermediate=0.5, Beginner=0.25
        """
        proficiency_map = {
            "expert": 1.0,
            "advanced": 0.75,
            "intermediate": 0.5,
            "beginner": 0.25,
        }

        relevant_scores = []
        for skill in skills:
            name = skill.get("name", "").lower()
            # Only score skills that are relevant to the JD
            if (name in self.required_skills_lower or
                name in self.preferred_skills_lower or
                self._is_semantically_relevant(name)):
                prof = skill.get("proficiency", "beginner")
                relevant_scores.append(proficiency_map.get(prof, 0.25))

        if not relevant_scores:
            return 0.0
        return sum(relevant_scores) / len(relevant_scores)

    def _compute_endorsement_score(self, skills: List[Dict]) -> float:
        """Score based on endorsements for relevant skills."""
        relevant_endorsements = []
        for skill in skills:
            name = skill.get("name", "").lower()
            if (name in self.required_skills_lower or
                name in self.preferred_skills_lower or
                self._is_semantically_relevant(name)):
                relevant_endorsements.append(skill.get("endorsements", 0))

        if not relevant_endorsements:
            return 0.0

        # Normalize: 50+ endorsements = max score
        avg_endorsements = sum(relevant_endorsements) / len(relevant_endorsements)
        return min(avg_endorsements / 50.0, 1.0)

    def _compute_assessment_score(self, signals: Dict) -> float:
        """Average assessment scores for relevant skills."""
        assessments = signals.get("skill_assessment_scores", {})
        if not assessments:
            return 0.0

        relevant_scores = []
        for skill_name, score in assessments.items():
            name_lower = skill_name.lower()
            if (name_lower in self.required_skills_lower or
                name_lower in self.preferred_skills_lower or
                self._is_semantically_relevant(name_lower)):
                relevant_scores.append(score / 100.0)

        if not relevant_scores:
            # Even non-relevant assessments show platform engagement
            all_scores = list(assessments.values())
            return (sum(all_scores) / len(all_scores) / 100.0) * 0.3  # discount
        return sum(relevant_scores) / len(relevant_scores)

    def _compute_depth_score(self, skills: List[Dict]) -> float:
        """
        Duration-weighted skill relevance.
        Long-used relevant skills are more trustworthy than recently added ones.
        """
        weighted_scores = []
        for skill in skills:
            name = skill.get("name", "").lower()
            duration = skill.get("duration_months", 0)
            if (name in self.required_skills_lower or
                name in self.preferred_skills_lower or
                self._is_semantically_relevant(name)):
                # Normalize duration: 36+ months = max
                duration_score = min(duration / 36.0, 1.0)
                weighted_scores.append(duration_score)

        if not weighted_scores:
            return 0.0
        return sum(weighted_scores) / len(weighted_scores)

    def _compute_semantic_score(self, candidate_skill_set: Set[str]) -> float:
        """
        How many of our semantic skill groups does the candidate cover?
        This rewards breadth across the capability areas we need.
        """
        groups_covered = 0
        total_groups = len(self.skill_synonyms)

        for group_name, group_skills in self.skill_synonyms.items():
            if candidate_skill_set & group_skills:
                groups_covered += 1

        return groups_covered / max(total_groups, 1)

    def _compute_skill_trust(self, skills: List[Dict]) -> float:
        """
        Trust signal: do endorsements correlate with duration?
        A skill with 50 endorsements but 1 month duration is suspicious.
        """
        if not skills:
            return 0.5  # neutral

        suspicious_count = 0
        for skill in skills:
            endorsements = skill.get("endorsements", 0)
            duration = skill.get("duration_months", 0)
            proficiency = skill.get("proficiency", "beginner")

            # High endorsements with very low duration
            if endorsements > 30 and duration < 6:
                suspicious_count += 1
            # Expert/advanced with zero duration
            if proficiency in ("expert", "advanced") and duration == 0:
                suspicious_count += 1

        penalty = suspicious_count / max(len(skills), 1)
        return max(1.0 - penalty, 0.0)

    def _is_semantically_relevant(self, skill_name: str) -> bool:
        """Check if a skill is semantically relevant to any group."""
        for group_skills in self.skill_synonyms.values():
            if skill_name in group_skills:
                return True
        return False
