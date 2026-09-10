"""
Advanced Skill Matcher.

Goes beyond simple keyword matching to understand skill semantics:
1. Skill taxonomy with parent/child relationships
2. Skill-to-JD-requirement mapping
3. Composite "role readiness" scoring
4. Skill credibility (cross-referencing endorsements, duration, assessments)
"""
from typing import Dict, List, Set, Tuple


class AdvancedSkillMatcher:
    """
    Advanced skill matching using taxonomy and multi-signal credibility.
    """

    # JD requirement areas mapped to acceptable skill evidence
    JD_REQUIREMENT_MAP = {
        "embeddings_retrieval": {
            "description": "Production experience with embeddings-based retrieval",
            "weight": 1.0,  # REQUIRED
            "skills": {
                "Embeddings", "Semantic Search", "Vector Search", "Dense Retrieval",
                "Sentence Transformers", "sentence-transformers", "FAISS", "Pinecone",
                "Weaviate", "Qdrant", "Milvus", "Chroma", "pgvector",
                "Information Retrieval", "Information Retrieval Systems",
                "Search & Discovery", "Search Backend", "Search Infrastructure",
                "BM25", "Lucene", "Solr", "OpenSearch", "Elasticsearch",
            },
        },
        "vector_databases": {
            "description": "Production experience with vector databases or hybrid search",
            "weight": 1.0,  # REQUIRED
            "skills": {
                "FAISS", "Pinecone", "Weaviate", "Qdrant", "Milvus",
                "OpenSearch", "Elasticsearch", "Chroma", "pgvector",
                "Vector Search", "Vector Database", "Hybrid Search",
            },
        },
        "python_strong": {
            "description": "Strong Python",
            "weight": 0.8,  # REQUIRED
            "skills": {
                "Python", "FastAPI", "Flask", "Django", "Pandas",
                "NumPy", "SciPy", "PyTorch", "TensorFlow",
            },
        },
        "evaluation_frameworks": {
            "description": "Evaluation frameworks for ranking",
            "weight": 0.8,  # REQUIRED
            "skills": {
                "NDCG", "MRR", "MAP", "Learning to Rank", "LTR",
                "A/B Testing", "Evaluation", "Metrics", "Ranking Evaluation",
                "Information Retrieval", "Search Relevance",
            },
        },
        "llm_finetuning": {
            "description": "LLM fine-tuning (preferred, not required)",
            "weight": 0.5,  # PREFERRED
            "skills": {
                "Fine-tuning LLMs", "LoRA", "QLoRA", "PEFT", "RLHF",
                "Hugging Face Transformers", "Transformers", "LLMs",
                "LangChain", "LlamaIndex", "Prompt Engineering",
            },
        },
        "learning_to_rank": {
            "description": "Learning-to-rank models (preferred)",
            "weight": 0.5,  # PREFERRED
            "skills": {
                "Learning to Rank", "LTR", "XGBoost", "LightGBM",
                "CatBoost", "Gradient Boosting", "Ranking Model",
            },
        },
        "ml_production": {
            "description": "ML production systems",
            "weight": 0.6,
            "skills": {
                "MLOps", "MLflow", "Weights & Biases", "Wandb",
                "Model Serving", "BentoML", "TorchServe", "Triton",
                "Kubeflow", "SageMaker", "Docker", "Kubernetes",
                "Model Deployment", "CI/CD", "ML Pipeline",
            },
        },
        "nlp_core": {
            "description": "Core NLP skills",
            "weight": 0.7,
            "skills": {
                "NLP", "Natural Language Processing", "Text Classification",
                "Named Entity Recognition", "Sentiment Analysis",
                "Transformers", "BERT", "GPT", "Hugging Face Transformers",
                "spaCy", "NLTK", "Deep Learning", "Neural Networks",
            },
        },
        "data_engineering": {
            "description": "Data engineering (supporting)",
            "weight": 0.3,
            "skills": {
                "Spark", "Airflow", "Kafka", "Data Pipelines",
                "Databricks", "dbt", "ETL", "Data Engineering",
                "Apache Beam", "Apache Flink", "Snowflake",
            },
        },
    }

    def compute_role_readiness(
        self,
        candidate_skills: List[Dict],
        career_descriptions: str = "",
    ) -> Dict[str, float]:
        """
        Compute how "role ready" the candidate is for each JD requirement area.

        Returns:
            Dict with area-specific scores and overall readiness.
        """
        # Build skill lookup (case-insensitive)
        candidate_skill_names = {s.get("name", "").lower() for s in candidate_skills}
        candidate_skill_details = {
            s.get("name", "").lower(): s for s in candidate_skills
        }

        # Also check career descriptions for skill evidence
        career_lower = career_descriptions.lower()

        scores = {}
        total_weighted_score = 0.0
        total_weight = 0.0

        for area_name, area_config in self.JD_REQUIREMENT_MAP.items():
            area_skills = area_config["skills"]
            weight = area_config["weight"]

            # Count matches (case-insensitive)
            matches = []
            for skill in area_skills:
                skill_lower = skill.lower()
                if skill_lower in candidate_skill_names:
                    matches.append(skill_lower)
                elif skill_lower in career_lower:
                    matches.append(skill_lower)  # found in career text

            # Score: how many of the area's skills does the candidate have?
            # But we cap at reasonable level (don't need ALL, just evidence)
            area_score = min(len(matches) / 3.0, 1.0)  # 3+ matches = full score

            # Boost if the matched skills have high credibility
            credibility_boost = 0.0
            for match in matches[:3]:
                if match in candidate_skill_details:
                    skill_data = candidate_skill_details[match]
                    # High proficiency + long duration + endorsements = credible
                    prof_score = {"expert": 1.0, "advanced": 0.75, "intermediate": 0.5, "beginner": 0.25}.get(
                        skill_data.get("proficiency", "beginner"), 0.25
                    )
                    duration_score = min(skill_data.get("duration_months", 0) / 24.0, 1.0)
                    endorse_score = min(skill_data.get("endorsements", 0) / 20.0, 1.0)
                    credibility_boost += (prof_score + duration_score + endorse_score) / 9.0

            area_score = min(area_score + credibility_boost, 1.0)

            scores[f"req_{area_name}"] = area_score
            total_weighted_score += area_score * weight
            total_weight += weight

        # Overall role readiness
        scores["role_readiness_score"] = (
            total_weighted_score / total_weight if total_weight > 0 else 0.0
        )

        # Required areas coverage (how many REQUIRED areas are covered?)
        required_areas = [
            name for name, cfg in self.JD_REQUIREMENT_MAP.items()
            if cfg["weight"] >= 0.8
        ]
        required_covered = sum(
            1 for area in required_areas if scores.get(f"req_{area}", 0) > 0.3
        )
        scores["required_coverage"] = required_covered / max(len(required_areas), 1)

        return scores
