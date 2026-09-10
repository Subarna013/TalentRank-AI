"""
Skill Canonicalization Layer.

Production talent search systems (LinkedIn, Eightfold) normalize skills into
a canonical taxonomy before matching. This prevents false negatives from:
- Abbreviations (ML vs Machine Learning)
- Synonyms (Deep Learning vs Neural Networks vs DL)
- Variations (PyTorch vs pytorch vs Torch)
- Hierarchy (NLP is-a Machine Learning, Embeddings is-a NLP)

Inspired by LinkedIn's SIGIR 2018 paper on canonical title/skill normalization.
"""
from typing import Dict, List, Set, Tuple


class SkillCanonicalizer:
    """
    Maps raw skill strings to canonical forms and provides
    taxonomic relationships between skills.
    """

    # Canonical skill taxonomy
    # Format: canonical_name -> {aliases}
    TAXONOMY = {
        # === Core ML/AI ===
        "machine_learning": {
            "machine learning", "ml", "applied ml", "applied machine learning",
            "statistical learning", "predictive modeling",
        },
        "deep_learning": {
            "deep learning", "dl", "neural networks", "neural network",
            "deep neural networks", "dnn",
        },
        "nlp": {
            "nlp", "natural language processing", "text processing",
            "computational linguistics", "text mining", "text analytics",
        },
        "computer_vision": {
            "computer vision", "cv", "image processing", "image recognition",
            "image classification", "object detection", "yolo",
            "image segmentation", "ocr",
        },
        "speech": {
            "speech recognition", "asr", "tts", "text to speech",
            "speech synthesis", "voice recognition", "speech processing",
        },
        "reinforcement_learning": {
            "reinforcement learning", "rl", "deep reinforcement learning",
            "policy gradient", "q-learning",
        },

        # === Retrieval & Ranking (JD CORE) ===
        "information_retrieval": {
            "information retrieval", "ir", "search relevance",
            "search ranking", "search quality", "search & discovery",
            "search backend", "search infrastructure",
            "search engine", "full-text search",
        },
        "embeddings": {
            "embeddings", "sentence transformers", "sentence-transformers",
            "word embeddings", "word2vec", "fasttext", "glove",
            "text embeddings", "semantic embeddings", "bge", "e5",
            "vector representations",
        },
        "vector_database": {
            "faiss", "pinecone", "weaviate", "qdrant", "milvus",
            "chroma", "pgvector", "opensearch", "elasticsearch",
            "vector search", "vector database", "similarity search",
            "ann", "approximate nearest neighbor", "hnsw",
        },
        "ranking_models": {
            "learning to rank", "ltr", "ranking", "ranking model",
            "lambdarank", "lambdamart", "ndcg", "mrr",
            "recommendation systems", "collaborative filtering",
            "content-based filtering",
        },
        "semantic_search": {
            "semantic search", "dense retrieval", "sparse retrieval",
            "hybrid search", "bm25", "tf-idf",
        },

        # === LLMs (JD PREFERRED) ===
        "llm": {
            "llm", "llms", "large language models", "language model",
            "gpt", "bert", "transformers", "transformer",
            "hugging face transformers", "huggingface",
        },
        "llm_finetuning": {
            "fine-tuning llms", "fine-tuning", "fine tuning",
            "lora", "qlora", "peft", "rlhf", "dpo",
            "adapter tuning", "instruction tuning",
        },
        "rag": {
            "rag", "retrieval augmented generation",
            "langchain", "llamaindex", "haystack",
        },
        "prompt_engineering": {
            "prompt engineering", "prompt design", "few-shot",
            "chain of thought", "prompt optimization",
        },

        # === ML Ops & Infra ===
        "mlops": {
            "mlops", "ml ops", "mlflow", "weights & biases", "wandb",
            "experiment tracking", "model registry",
            "bentoml", "torchserve", "triton",
        },
        "model_serving": {
            "model serving", "model deployment", "inference",
            "inference optimization", "model optimization",
            "onnx", "tensorrt", "quantization",
        },

        # === Programming ===
        "python": {
            "python", "python3", "cpython",
        },
        "python_ml_stack": {
            "pytorch", "tensorflow", "keras", "jax",
            "scikit-learn", "sklearn", "xgboost", "lightgbm",
            "catboost", "numpy", "scipy", "pandas",
        },

        # === Data Engineering ===
        "data_engineering": {
            "spark", "pyspark", "airflow", "kafka",
            "data pipelines", "data engineering", "etl",
            "dbt", "databricks", "apache beam", "apache flink",
            "snowflake", "bigquery",
        },

        # === Cloud & Infra ===
        "cloud": {
            "aws", "gcp", "azure", "sagemaker",
            "cloud computing", "cloud infrastructure",
        },
        "containerization": {
            "docker", "kubernetes", "k8s", "container",
            "microservices",
        },
    }

    # Which canonical categories are relevant to the JD?
    JD_CORE_CATEGORIES = {
        "information_retrieval", "embeddings", "vector_database",
        "ranking_models", "semantic_search", "nlp",
    }
    JD_PREFERRED_CATEGORIES = {
        "llm_finetuning", "llm", "rag", "mlops", "model_serving",
        "python", "python_ml_stack",
    }
    JD_ANTI_CATEGORIES = {
        "computer_vision", "speech", "reinforcement_learning",
    }

    def __init__(self):
        # Build reverse lookup: alias -> canonical name
        self._alias_to_canonical: Dict[str, str] = {}
        for canonical, aliases in self.TAXONOMY.items():
            for alias in aliases:
                self._alias_to_canonical[alias.lower()] = canonical

    def canonicalize_skill(self, raw_skill: str) -> str:
        """Map a raw skill name to its canonical form."""
        lower = raw_skill.lower().strip()
        return self._alias_to_canonical.get(lower, lower)

    def canonicalize_skills(self, skills: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group candidate's skills by canonical category.

        Returns:
            Dict of canonical_name -> list of matching skill objects
        """
        grouped: Dict[str, List[Dict]] = {}
        for skill in skills:
            canonical = self.canonicalize_skill(skill.get("name", ""))
            if canonical not in grouped:
                grouped[canonical] = []
            grouped[canonical].append(skill)
        return grouped

    def compute_jd_coverage(self, skills: List[Dict], career_text: str = "") -> Dict[str, float]:
        """
        Compute how well a candidate covers the JD requirements using
        canonical skill mapping.

        Returns detailed coverage metrics.
        """
        # Get canonical skills from skill list
        canonical_skills = set()
        for skill in skills:
            canonical = self.canonicalize_skill(skill.get("name", ""))
            canonical_skills.add(canonical)

        # Also infer skills from career text
        career_lower = career_text.lower()
        for canonical, aliases in self.TAXONOMY.items():
            if canonical in canonical_skills:
                continue
            for alias in aliases:
                if alias in career_lower:
                    canonical_skills.add(canonical)
                    break

        # Compute coverage
        core_covered = canonical_skills & self.JD_CORE_CATEGORIES
        preferred_covered = canonical_skills & self.JD_PREFERRED_CATEGORIES
        anti_covered = canonical_skills & self.JD_ANTI_CATEGORIES

        # Scores
        core_coverage = len(core_covered) / max(len(self.JD_CORE_CATEGORIES), 1)
        preferred_coverage = len(preferred_covered) / max(len(self.JD_PREFERRED_CATEGORIES), 1)
        anti_ratio = len(anti_covered) / max(len(canonical_skills), 1)

        # Weighted score
        # Core matters most, preferred is a bonus, anti is a penalty
        overall = (
            0.60 * core_coverage +
            0.30 * preferred_coverage -
            0.10 * anti_ratio
        )

        return {
            "canonical_core_coverage": core_coverage,
            "canonical_preferred_coverage": preferred_coverage,
            "canonical_anti_ratio": anti_ratio,
            "canonical_overall_score": max(overall, 0.0),
            "core_categories_covered": len(core_covered),
            "preferred_categories_covered": len(preferred_covered),
            "total_canonical_categories": len(canonical_skills),
        }

    def infer_latent_skills(self, career_history: List[Dict]) -> Set[str]:
        """
        Infer skills that the candidate likely has but didn't list,
        based on what their career descriptions mention.

        This is how production systems catch hidden gems — a candidate who
        'built a recommendation system at scale' has ranking/retrieval skills
        even if they didn't explicitly list 'information retrieval'.
        """
        career_text = " ".join(
            job.get("description", "") for job in career_history
        ).lower()

        inferred = set()
        for canonical, aliases in self.TAXONOMY.items():
            for alias in aliases:
                if alias in career_text:
                    inferred.add(canonical)
                    break

        return inferred
