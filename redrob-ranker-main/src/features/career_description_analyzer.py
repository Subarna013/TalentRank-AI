"""
Career Description Deep Analyzer.

Goes beyond title matching to analyze what the candidate ACTUALLY DID
in their career. This catches:
1. Hidden gems: people with great experience but modest titles
2. Keyword stuffers: impressive titles but vague descriptions
3. Domain expertise: specific mentions of retrieval, ranking, search systems
"""
from typing import Dict, List, Tuple


class CareerDescriptionAnalyzer:
    """
    Deep semantic analysis of career history descriptions.
    Identifies candidates who have actually built retrieval/ranking/ML systems
    regardless of their title.
    """

    # Phrases that indicate the candidate has built what Redrob needs
    STRONG_EVIDENCE_PHRASES = [
        # Retrieval & Search
        "search relevance", "search ranking", "search quality",
        "retrieval system", "information retrieval", "search engine",
        "hybrid search", "semantic search", "vector search",
        "candidate ranking", "query understanding",
        "search infrastructure", "search backend",
        # Ranking & Recommendation
        "ranking system", "ranking model", "learning to rank",
        "recommendation system", "recommendation engine",
        "personalization", "content ranking",
        "relevance model", "relevance scoring",
        "re-ranking", "reranking",
        # Embeddings & Vectors
        "embedding", "vector database", "vector index",
        "sentence transformer", "similarity search",
        "dense retrieval", "sparse retrieval",
        # Evaluation
        "ndcg", "mrr", "a/b test", "ab test",
        "offline evaluation", "online evaluation",
        "evaluation framework", "evaluation metric",
        # ML Systems
        "model serving", "model deployment", "inference",
        "feature store", "feature engineering",
        "training pipeline", "ml pipeline",
        # NLP Specifics
        "nlp pipeline", "text classification", "named entity",
        "language model", "fine-tuning", "fine-tune",
        "transformer", "bert", "gpt",
    ]

    # Phrases indicating production-level work (not just experiments)
    PRODUCTION_PHRASES = [
        "production", "deployed", "shipped", "launched",
        "serving", "real-time", "real time",
        "scale", "million", "billion",
        "latency", "throughput", "sla",
        "users", "traffic", "requests per second",
        "monitoring", "alerting", "on-call",
    ]

    # Phrases indicating IC work (actually wrote code, not just managed)
    IC_WORK_PHRASES = [
        "implemented", "built", "designed", "architected",
        "developed", "coded", "wrote", "created",
        "optimized", "improved", "reduced", "increased",
        "refactored", "migrated", "integrated",
    ]

    def analyze(self, career_history: List[Dict]) -> Dict[str, float]:
        """
        Analyze all career descriptions and return evidence scores.
        """
        features = {}

        all_descriptions = " ".join(
            job.get("description", "") for job in career_history
        ).lower()

        # 1. Domain evidence score (has this person built what we need?)
        strong_hits = sum(
            1 for phrase in self.STRONG_EVIDENCE_PHRASES
            if phrase in all_descriptions
        )
        features["domain_evidence_score"] = min(
            strong_hits / 8.0, 1.0  # 8+ hits = max score
        )
        features["domain_evidence_count"] = strong_hits

        # 2. Production evidence (did they ship to real users?)
        prod_hits = sum(
            1 for phrase in self.PRODUCTION_PHRASES
            if phrase in all_descriptions
        )
        features["production_evidence_score"] = min(
            prod_hits / 5.0, 1.0  # 5+ hits = max score
        )

        # 3. IC work evidence (did they actually code?)
        ic_hits = sum(
            1 for phrase in self.IC_WORK_PHRASES
            if phrase in all_descriptions
        )
        features["ic_work_score"] = min(
            ic_hits / 5.0, 1.0
        )

        # 4. Description depth (how detailed are the descriptions?)
        total_words = len(all_descriptions.split())
        features["description_depth_score"] = min(
            total_words / 500.0, 1.0  # 500+ words = rich descriptions
        )

        # 5. Specificity score (mentions specific technologies, numbers, metrics)
        specifics = self._count_specifics(all_descriptions)
        features["specificity_score"] = min(specifics / 10.0, 1.0)

        # 6. Role progression in domain
        features["domain_continuity_score"] = self._compute_domain_continuity(
            career_history
        )

        return features

    def _count_specifics(self, text: str) -> int:
        """Count specific technical mentions and metrics."""
        specifics = 0

        # Technology names
        tech_names = [
            "elasticsearch", "solr", "lucene", "faiss", "pinecone",
            "weaviate", "qdrant", "milvus", "redis", "postgresql",
            "kafka", "spark", "airflow", "kubernetes", "docker",
            "pytorch", "tensorflow", "huggingface", "scikit",
            "xgboost", "lightgbm", "catboost",
            "python", "java", "go", "rust", "scala",
            "aws", "gcp", "azure", "s3", "sagemaker",
        ]
        for tech in tech_names:
            if tech in text:
                specifics += 1

        # Numbers (indicates measurable impact)
        import re
        numbers = re.findall(r'\d+[kmb%]|\d+\.\d+|\d{2,}', text)
        specifics += min(len(numbers), 5)

        return specifics

    def _compute_domain_continuity(self, career: List[Dict]) -> float:
        """
        How many roles in a row were in a relevant domain?
        Continuous domain experience is stronger signal than one-off.
        """
        if not career:
            return 0.0

        relevant_keywords = [
            "ml", "ai", "machine learning", "data science", "nlp",
            "search", "ranking", "recommendation", "retrieval",
            "backend", "engineer", "developer", "scientist",
        ]

        consecutive_relevant = 0
        max_consecutive = 0

        for job in career:
            title = job.get("title", "").lower()
            desc = job.get("description", "").lower()
            combined = f"{title} {desc}"

            is_relevant = any(kw in combined for kw in relevant_keywords)
            if is_relevant:
                consecutive_relevant += 1
                max_consecutive = max(max_consecutive, consecutive_relevant)
            else:
                consecutive_relevant = 0

        return min(max_consecutive / 3.0, 1.0)  # 3+ consecutive = max
