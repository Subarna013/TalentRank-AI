"""
Offline Pipeline.

Pre-computes artifacts that the online ranker can use:
1. Feature extraction for all candidates → parquet
2. Embedding generation → numpy arrays
3. Index building → FAISS indexes
4. LTR model training (self-supervised) → LightGBM model

This pipeline can exceed the 5-minute limit since it runs before ranking.
"""
import json
import logging
import pickle
import time
from pathlib import Path
from typing import Dict, List

import numpy as np

from src.config.settings import Settings, get_settings
from src.core.types import Candidate, FeatureVector
from src.features.feature_registry import FeatureRegistry
from src.validators.honeypot_detector import HoneypotDetector

logger = logging.getLogger(__name__)


class OfflinePipeline:
    """
    Pre-computation pipeline. Runs once before the competition ranking.
    Produces artifacts used by the online ranker.
    """

    def __init__(self, settings: Settings = None):
        self.settings = settings or get_settings()
        self.feature_registry = FeatureRegistry(self.settings)
        self.honeypot_detector = HoneypotDetector(self.settings)

    def run(self, candidates_path: str) -> Dict[str, str]:
        """
        Execute the full offline pipeline.

        Returns:
            Dict of artifact_name -> file_path for all produced artifacts.
        """
        start = time.time()
        logger.info("Starting offline pipeline...")
        artifacts = {}

        # Load candidates
        candidates = self._load_candidates(candidates_path)
        logger.info(f"Loaded {len(candidates)} candidates")

        # Phase 1: Validate and detect honeypots
        logger.info("Phase 1: Honeypot detection...")
        honeypot_data = {}
        for candidate in candidates:
            is_honeypot, reasons, penalty = self.honeypot_detector.detect(candidate)
            candidate.is_honeypot = is_honeypot
            candidate.trust_score = max(1.0 + penalty, 0.0)
            if is_honeypot:
                honeypot_data[candidate.candidate_id] = {
                    "reasons": reasons,
                    "penalty": penalty,
                }

        # Save honeypot data
        hp_path = self.settings.paths.metadata_dir / "honeypots.json"
        hp_path.parent.mkdir(parents=True, exist_ok=True)
        with open(hp_path, 'w') as f:
            json.dump(honeypot_data, f, indent=2)
        artifacts["honeypots"] = str(hp_path)
        logger.info(f"  Detected {len(honeypot_data)} honeypots → {hp_path}")

        # Phase 2: Feature extraction for all candidates
        logger.info("Phase 2: Feature extraction...")
        feature_data = {}
        for i, candidate in enumerate(candidates):
            fv = self.feature_registry.compute_features(candidate)
            feature_data[candidate.candidate_id] = fv.to_array()

            if (i + 1) % 10000 == 0:
                logger.info(f"  Processed {i + 1}/{len(candidates)} candidates")

        # Save features
        features_path = self.settings.paths.metadata_dir / "candidate_features.pkl"
        with open(features_path, 'wb') as f:
            pickle.dump(feature_data, f)
        artifacts["features"] = str(features_path)
        logger.info(f"  Features saved → {features_path}")

        # Phase 3: Generate embeddings (if sentence-transformers available)
        try:
            logger.info("Phase 3: Embedding generation...")
            self._generate_embeddings(candidates, artifacts)
        except ImportError:
            logger.warning("  sentence-transformers not installed, skipping embeddings")

        # Phase 4: Build feature registry metadata
        logger.info("Phase 4: Building feature registry metadata...")
        registry_path = self.settings.paths.metadata_dir / "feature_registry.json"
        registry_meta = {
            "feature_names": FeatureVector.feature_names(),
            "n_features": len(FeatureVector.feature_names()),
            "n_candidates": len(candidates),
            "n_honeypots": len(honeypot_data),
        }
        with open(registry_path, 'w') as f:
            json.dump(registry_meta, f, indent=2)
        artifacts["feature_registry"] = str(registry_path)

        elapsed = time.time() - start
        logger.info(f"Offline pipeline complete in {elapsed:.1f}s")
        logger.info(f"Artifacts: {list(artifacts.keys())}")

        return artifacts

    def _generate_embeddings(self, candidates: List[Candidate], artifacts: Dict):
        """Generate and save multi-view embeddings."""
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(self.settings.retrieval.embedding_model)
        views = self.settings.retrieval.views

        for view in views:
            logger.info(f"  Generating {view} embeddings...")
            texts = [self._get_view_text(c, view) for c in candidates]

            embeddings = model.encode(
                texts,
                batch_size=256,
                show_progress_bar=True,
                normalize_embeddings=True,
            )

            emb_path = self.settings.paths.embeddings_dir / f"{view}_embeddings.npy"
            emb_path.parent.mkdir(parents=True, exist_ok=True)
            np.save(emb_path, embeddings)
            artifacts[f"embeddings_{view}"] = str(emb_path)
            logger.info(f"  Saved {view} embeddings: {embeddings.shape} → {emb_path}")

        # Save candidate ID order
        ids_path = self.settings.paths.embeddings_dir / "candidate_ids.json"
        with open(ids_path, 'w') as f:
            json.dump([c.candidate_id for c in candidates], f)
        artifacts["candidate_ids"] = str(ids_path)

    def _get_view_text(self, candidate: Candidate, view: str) -> str:
        """Generate text for a specific embedding view."""
        if view == "career_summary":
            parts = [candidate.headline, candidate.summary]
            for job in candidate.career_history[:3]:
                parts.append(f"{job.get('title', '')} at {job.get('company', '')}")
                parts.append(job.get("description", ""))
            return " ".join(filter(None, parts))

        elif view == "skills_title":
            parts = [candidate.current_title, candidate.headline]
            for skill in candidate.skills:
                parts.append(f"{skill.get('name', '')} ({skill.get('proficiency', '')})")
            for cert in candidate.certifications:
                parts.append(cert.get("name", ""))
            return " ".join(filter(None, parts))

        elif view == "responsibilities":
            parts = [job.get("description", "") for job in candidate.career_history]
            return " ".join(filter(None, parts)) or candidate.summary

        return f"{candidate.headline} {candidate.summary}"

    def _load_candidates(self, path: str) -> List[Candidate]:
        """Load candidates from JSONL."""
        import gzip

        candidates = []
        file_path = Path(path)

        if file_path.suffix == '.gz':
            open_fn = lambda: gzip.open(file_path, 'rt', encoding='utf-8')
        else:
            open_fn = lambda: open(file_path, 'r', encoding='utf-8')

        with open_fn() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                profile = data.get("profile", {})
                candidate = Candidate(
                    candidate_id=data["candidate_id"],
                    headline=profile.get("headline", ""),
                    summary=profile.get("summary", ""),
                    location=profile.get("location", ""),
                    country=profile.get("country", ""),
                    years_of_experience=profile.get("years_of_experience", 0.0),
                    current_title=profile.get("current_title", ""),
                    current_company=profile.get("current_company", ""),
                    current_company_size=profile.get("current_company_size", ""),
                    current_industry=profile.get("current_industry", ""),
                    career_history=data.get("career_history", []),
                    education=data.get("education", []),
                    skills=data.get("skills", []),
                    certifications=data.get("certifications", []),
                    languages=data.get("languages", []),
                    redrob_signals=data.get("redrob_signals", {}),
                )
                candidates.append(candidate)

        return candidates
