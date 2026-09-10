"""
Central configuration for the entire ranking system.
All thresholds, weights, paths, and model parameters live here.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class PathConfig:
    """File and directory paths."""
    project_root: Path = Path(".")
    data_dir: Path = Path("./data")
    artifacts_dir: Path = Path("./artifacts")
    models_dir: Path = Path("./artifacts/models")
    indexes_dir: Path = Path("./artifacts/indexes")
    embeddings_dir: Path = Path("./artifacts/embeddings")
    metadata_dir: Path = Path("./artifacts/metadata")
    candidates_file: Path = Path("./data/candidates.jsonl")
    output_file: Path = Path("./submission.csv")


@dataclass
class JDConfig:
    """Job description requirements extracted from the JD."""
    # Core requirements
    title_keywords: List[str] = field(default_factory=lambda: [
        "AI Engineer", "ML Engineer", "Machine Learning Engineer",
        "Senior AI Engineer", "Applied ML", "NLP Engineer",
        "Search Engineer", "Ranking Engineer", "Data Scientist"
    ])
    required_skills: List[str] = field(default_factory=lambda: [
        "embeddings", "retrieval", "ranking", "vector databases",
        "sentence-transformers", "FAISS", "Pinecone", "Weaviate",
        "Qdrant", "Milvus", "OpenSearch", "Elasticsearch",
        "Python", "NLP", "information retrieval",
        "NDCG", "MRR", "MAP", "A/B testing", "evaluation frameworks"
    ])
    preferred_skills: List[str] = field(default_factory=lambda: [
        "LLM fine-tuning", "LoRA", "QLoRA", "PEFT",
        "learning-to-rank", "XGBoost", "LightGBM",
        "HR tech", "recruiting tech", "marketplace",
        "distributed systems", "inference optimization",
        "open-source contributions"
    ])
    anti_skills: List[str] = field(default_factory=lambda: [
        # Skills that indicate wrong domain focus
        "computer vision", "speech recognition", "robotics",
        "TTS", "image classification", "object detection", "GANs"
    ])
    experience_range: tuple = (5, 9)  # years
    experience_hard_min: float = 3.0  # absolute minimum
    experience_hard_max: float = 15.0  # diminishing returns beyond this
    preferred_locations: List[str] = field(default_factory=lambda: [
        "India", "Pune", "Noida", "Hyderabad", "Mumbai",
        "Delhi", "Delhi NCR", "Gurgaon", "Bangalore", "Bengaluru",
        "Chennai", "Kolkata"
    ])
    preferred_countries: List[str] = field(default_factory=lambda: [
        "India"
    ])
    disqualifying_industries: List[str] = field(default_factory=lambda: [
        # Pure consulting/services without product experience
    ])
    consulting_companies: List[str] = field(default_factory=lambda: [
        "TCS", "Infosys", "Wipro", "Accenture", "Cognizant",
        "Capgemini", "HCL Technologies", "Tech Mahindra"
    ])
    max_notice_period_days: int = 90  # strong preference for <30, accept up to 90
    preferred_work_modes: List[str] = field(default_factory=lambda: [
        "hybrid", "onsite", "flexible"
    ])
    # The JD is for a product company; penalize pure services/consulting backgrounds
    product_company_bonus: float = 0.15


@dataclass
class RetrievalConfig:
    """Retrieval stage parameters."""
    bm25_top_k: int = 3000
    dense_top_k: int = 2000
    rrf_k: int = 60  # RRF constant (standard is 60)
    rrf_top_k: int = 1000  # candidates after fusion
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    faiss_nprobe: int = 32
    # Multi-view embedding fields
    views: List[str] = field(default_factory=lambda: [
        "career_summary",  # headline + summary + career descriptions
        "skills_title",    # skills + titles combined
        "responsibilities" # career history descriptions
    ])


@dataclass
class RankingConfig:
    """LTR model parameters."""
    model_type: str = "lightgbm_lambdarank"
    n_estimators: int = 300
    num_leaves: int = 63
    learning_rate: float = 0.05
    min_child_samples: int = 20
    feature_importance_type: str = "gain"
    # Since we don't have ground truth labels, we use a self-supervised approach
    # using synthetic relevance derived from our feature signals
    synthetic_relevance_tiers: int = 5


@dataclass
class ScoringWeights:
    """Weights for the composite scoring model."""
    # Feature family weights (sum to 1.0)
    skills_match: float = 0.30
    career_relevance: float = 0.25
    experience_fit: float = 0.15
    education: float = 0.05
    behavioral: float = 0.15
    trust_score: float = 0.10

    # Sub-weights within skills
    skill_semantic_match: float = 0.40
    skill_proficiency_depth: float = 0.25
    skill_endorsement_signal: float = 0.15
    skill_assessment_score: float = 0.20

    # Sub-weights within career
    career_title_relevance: float = 0.30
    career_trajectory: float = 0.20
    career_company_type: float = 0.25  # product vs services
    career_stability: float = 0.15
    career_recency: float = 0.10

    # Sub-weights within behavioral
    engagement_score: float = 0.25
    availability_score: float = 0.30
    platform_trust: float = 0.25
    recruiter_interest: float = 0.20


@dataclass
class HoneypotConfig:
    """Honeypot detection thresholds."""
    # Impossible profile indicators
    max_skills_with_zero_duration: int = 3
    max_expert_skills_low_experience: int = 2  # expert in 5+ skills with <3 yrs
    min_experience_for_expert_count: float = 3.0
    company_founding_check: bool = True
    # Anomaly thresholds
    skill_inflation_threshold: float = 0.8  # ratio of expert/advanced to total skills
    career_gap_impossible_days: int = -30  # overlapping jobs shouldn't be negative
    future_date_tolerance_days: int = 30
    # Scoring
    honeypot_penalty: float = -1.0  # effectively removes from ranking


@dataclass
class Settings:
    """Master settings object."""
    paths: PathConfig = field(default_factory=PathConfig)
    jd: JDConfig = field(default_factory=JDConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    ranking: RankingConfig = field(default_factory=RankingConfig)
    weights: ScoringWeights = field(default_factory=ScoringWeights)
    honeypot: HoneypotConfig = field(default_factory=HoneypotConfig)
    # Global
    top_k_output: int = 100
    random_seed: int = 42
    n_workers: int = 4
    verbose: bool = True


# Singleton
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
