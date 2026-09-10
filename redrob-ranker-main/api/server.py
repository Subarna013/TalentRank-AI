"""
FastAPI Backend — Redrob AI Ranker

Production REST API for the candidate ranking engine.

Run:
    uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload

Endpoints:
    POST /api/rank           — Rank candidates against the JD
    POST /api/explain        — Deep explainability for one candidate
    POST /api/compare        — Compare multiple candidates side-by-side
    GET  /api/health         — System health check
    GET  /api/config         — Current scoring configuration
"""
import json
import time
import sys
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import get_settings
from src.core.types import Candidate
from src.features.feature_registry import FeatureRegistry
from src.validators.honeypot_detector import HoneypotDetector
from src.reasoning.explanation_engine import ExplanationEngine
from src.features.skill_canonicalizer import SkillCanonicalizer
from src.features.mutual_interest_scorer import MutualInterestScorer


# ─────────── APP SETUP ───────────

app = FastAPI(
    title="Redrob AI Ranker",
    description="Intelligent Candidate Discovery & Ranking System — REST API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Engine initialization
settings = get_settings()
feature_registry = FeatureRegistry(settings)
honeypot_detector = HoneypotDetector(settings)
explanation_engine = ExplanationEngine(settings)
canonicalizer = SkillCanonicalizer()
mutual_interest_scorer = MutualInterestScorer(settings)


# ─────────── MODELS ───────────

class RankRequest(BaseModel):
    candidates: List[dict] = Field(..., description="List of candidate profile objects")
    top_k: int = Field(100, ge=1, le=1000, description="Number of top candidates to return")


class CandidateResult(BaseModel):
    candidate_id: str
    rank: int
    score: float
    reasoning: str
    title: str
    company: str
    years_of_experience: float
    location: str
    country: str
    is_honeypot: bool
    trust_score: float
    features: dict


class RankResponse(BaseModel):
    results: List[CandidateResult]
    metadata: dict


class ExplainRequest(BaseModel):
    candidate: dict = Field(..., description="Single candidate profile object")


class CompareRequest(BaseModel):
    candidates: List[dict] = Field(..., description="List of candidate profiles to compare")


# ─────────── HELPERS ───────────

def _parse(data: dict) -> Candidate:
    p = data.get("profile", {})
    return Candidate(
        candidate_id=data["candidate_id"],
        headline=p.get("headline", ""), summary=p.get("summary", ""),
        location=p.get("location", ""), country=p.get("country", ""),
        years_of_experience=p.get("years_of_experience", 0.0),
        current_title=p.get("current_title", ""),
        current_company=p.get("current_company", ""),
        current_company_size=p.get("current_company_size", ""),
        current_industry=p.get("current_industry", ""),
        career_history=data.get("career_history", []),
        education=data.get("education", []),
        skills=data.get("skills", []),
        certifications=data.get("certifications", []),
        languages=data.get("languages", []),
        redrob_signals=data.get("redrob_signals", {}),
    )


def _score_candidate(c: Candidate) -> dict:
    """Score a single candidate and return full feature breakdown."""
    is_hp, reasons, penalty = honeypot_detector.detect(c)
    c.is_honeypot = is_hp
    c.honeypot_reasons = reasons
    c.trust_score = max(1.0 + penalty, 0.0)

    fv = feature_registry.compute_features(c)
    score = feature_registry.compute_composite_score(fv)

    career_text = " ".join(j.get("description", "") for j in c.career_history)
    canonical = canonicalizer.compute_jd_coverage(c.skills, career_text)
    mi = mutual_interest_scorer.compute(c.redrob_signals, {"country": c.country})

    return {
        "candidate": c,
        "score": score,
        "fv": fv,
        "canonical": canonical,
        "mutual_interest": mi,
        "honeypot": {"is_honeypot": is_hp, "reasons": reasons, "trust": c.trust_score},
    }


# ─────────── ENDPOINTS ───────────

@app.get("/api/health")
async def health():
    """System health check."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "engine": "loaded",
        "features": 45,
        "canonical_categories": len(canonicalizer.TAXONOMY),
    }


@app.get("/api/config")
async def get_config():
    """Return current scoring configuration."""
    return {
        "jd_title": "Senior AI Engineer — Founding Team",
        "jd_company": "Redrob AI (Series A)",
        "experience_range": [5, 9],
        "preferred_locations": settings.jd.preferred_locations,
        "scoring_architecture": "4-pass quality × mutual interest",
        "passes": [
            "Pass 1: Canonical skill coverage (structured taxonomy match)",
            "Pass 2: Career evidence (NLP on career descriptions)",
            "Pass 3: Role readiness (9-area requirement mapping)",
            "Pass 4: Experience & trajectory fit",
        ],
        "modifiers": [
            "Mutual Interest (response probability × interest × hireability)",
            "Location (India required)",
            "Trust Score (honeypot detection)",
            "Career Consistency",
        ],
    }
@app.post("/api/rank", response_model=RankResponse)
async def rank_candidates(request: RankRequest):

    print("=" * 60)
    print("RANK API CALLED")
    print(request.candidates)
    print("=" * 60)

    if not request.candidates:
        raise HTTPException(400, "No candidates provided")

    scored = []
    honeypot_count = 0
    start = time.time()

    for data in request.candidates:

        try:
            candidate = _parse(data)

            print(candidate)

            result = _score_candidate(candidate)

            if result["honeypot"]["is_honeypot"]:
                honeypot_count += 1
                continue

            scored.append(result)

        except Exception:
            import traceback

            traceback.print_exc()

            print("BAD CANDIDATE")
            print(data)

    scored.sort(
        key=lambda x: (-x["score"], x["candidate"].candidate_id)
    )

    top = scored[: request.top_k]

    results = []

    for rank, item in enumerate(top, 1):

        c = item["candidate"]
        fv = item["fv"]

        reasoning = explanation_engine.generate(
            c,
            fv,
            rank,
            item["score"],
        )

        results.append(
            CandidateResult(
                candidate_id=c.candidate_id,
                rank=rank,
                score=round(item["score"], 4),
                reasoning=reasoning,
                title=c.current_title,
                company=c.current_company,
                years_of_experience=c.years_of_experience,
                location=c.location,
                country=c.country,
                is_honeypot=False,
                trust_score=round(c.trust_score, 3),
                features={}
            )
        )

    return RankResponse(
        results=results,
        metadata={
            "total_input": len(request.candidates),
            "candidates_ranked": len(results),
            "honeypots_filtered": honeypot_count,
            "runtime_seconds": round(time.time() - start, 3),
            "top_k": request.top_k,
        },
    )


@app.post("/api/explain")
async def explain_candidate(request: ExplainRequest):
    """Deep explainability for a single candidate."""
    result = _score_candidate(_parse(request.candidate))
    c = result["candidate"]
    fv = result["fv"]

    reasoning = explanation_engine.generate(c, fv, 1, result["score"])

    return {
        "candidate_id": c.candidate_id,
        "overall_score": round(result["score"], 4),
        "reasoning": reasoning,
        "honeypot_analysis": result["honeypot"],
        "canonical_skills": result["canonical"],
        "mutual_interest": result["mutual_interest"],
        "feature_breakdown": {
            "skills": {
                "semantic_score": round(fv.skill_semantic_score, 3),
                "proficiency_score": round(fv.skill_proficiency_score, 3),
                "depth_score": round(fv.skill_depth_score, 3),
                "endorsement_score": round(fv.skill_endorsement_score, 3),
                "anti_skill_penalty": round(fv.anti_skill_penalty, 3),
                "required_count": fv.required_skill_count,
                "preferred_count": fv.preferred_skill_count,
            },
            "career": {
                "title_relevance": round(fv.title_relevance_score, 3),
                "trajectory": round(fv.career_trajectory_score, 3),
                "product_company_ratio": round(fv.product_company_ratio, 3),
                "consulting_only": fv.consulting_only_flag,
                "stability": round(fv.career_stability_score, 3),
                "recency": round(fv.career_recency_score, 3),
                "consistency": round(fv.career_consistency_score, 3),
            },
            "experience": {
                "fit_score": round(fv.experience_fit_score, 3),
                "years": fv.years_of_experience,
                "in_range": fv.experience_in_range,
                "domain_months": fv.domain_experience_months,
            },
            "behavioral": {
                "engagement": round(fv.engagement_score, 3),
                "availability": round(fv.availability_score, 3),
                "platform_trust": round(fv.platform_trust_score, 3),
                "recruiter_interest": round(fv.recruiter_interest_score, 3),
            },
            "location": {
                "match": fv.location_match,
                "relocate": fv.willing_to_relocate,
                "work_mode_match": fv.preferred_work_mode_match,
            },
        },
    }


@app.post("/api/compare")
async def compare_candidates(request: CompareRequest):
    """Side-by-side comparison of multiple candidates."""
    if len(request.candidates) > 20:
        raise HTTPException(400, "Max 20 candidates for comparison")

    comparisons = []
    for data in request.candidates:
        result = _score_candidate(_parse(data))
        c = result["candidate"]
        fv = result["fv"]
        comparisons.append({
            "candidate_id": c.candidate_id,
            "title": c.current_title,
            "company": c.current_company,
            "years": c.years_of_experience,
            "country": c.country,
            "score": round(result["score"], 4),
            "technical_fit": round(
                result["canonical"].get("canonical_core_coverage", 0), 3
            ),
            "career_evidence": round(
                getattr(fv, '_desc_features', {}).get("domain_evidence_score", 0), 3
            ),
            "mutual_interest": round(
                result["mutual_interest"].get("mutual_interest_score", 0), 3
            ),
            "trust": round(c.trust_score, 3),
            "is_honeypot": result["honeypot"]["is_honeypot"],
        })

    comparisons.sort(key=lambda x: -x["score"])
    return {"candidates": comparisons, "count": len(comparisons)}


@app.post("/api/stats")
async def compute_stats(request: RankRequest):
    """
    Quick statistics for a batch of candidates without full ranking.
    Useful for analytics previews and dashboard summaries.
    """
    if not request.candidates:
        raise HTTPException(400, "No candidates provided")

    total = len(request.candidates)
    locations = {}
    industries = {}
    experience_sum = 0.0
    skills_counter = {}

    for data in request.candidates:
        p = data.get("profile", {})

        # Location stats
        loc = p.get("location", "") or p.get("country", "Unknown")
        locations[loc] = locations.get(loc, 0) + 1

        # Industry stats
        ind = p.get("current_industry", "Unknown") or "Unknown"
        industries[ind] = industries.get(ind, 0) + 1

        # Experience
        experience_sum += float(p.get("years_of_experience", 0) or 0)

        # Skills
        for skill in data.get("skills", []):
            name = skill.get("name", "Unknown") if isinstance(skill, dict) else str(skill)
            skills_counter[name] = skills_counter.get(name, 0) + 1

    # Sort and limit
    top_locations = sorted(locations.items(), key=lambda x: -x[1])[:10]
    top_industries = sorted(industries.items(), key=lambda x: -x[1])[:10]
    top_skills = sorted(skills_counter.items(), key=lambda x: -x[1])[:20]

    return {
        "total_candidates": total,
        "avg_experience": round(experience_sum / max(total, 1), 1),
        "top_locations": [{"name": k, "count": v} for k, v in top_locations],
        "top_industries": [{"name": k, "count": v} for k, v in top_industries],
        "top_skills": [{"name": k, "count": v} for k, v in top_skills],
        "unique_locations": len(locations),
        "unique_skills": len(skills_counter),
    }
