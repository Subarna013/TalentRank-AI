import streamlit as st
import pandas as pd
import json
import time
from pathlib import Path

from utils.api_client import rank_candidates


def upload_section():
    """Upload CSV/JSON/JSONL and send to backend for ranking."""

    # Compact upload area matching admin design
    with st.container(border=True):
        col_upload, col_demo = st.columns([3, 1])

        with col_upload:
            st.markdown("**📂 Upload Resumes**")
            st.caption("CSV, JSON, or JSONL format supported")

        with col_demo:
            demo_clicked = st.button("🚀 Demo", use_container_width=True,
                                      help="Load 50 sample candidates")

    # Handle demo data load
    if demo_clicked:
        return _load_demo_data()

    uploaded = st.file_uploader(
        "Upload Candidate Dataset",
        type=["csv", "json", "jsonl"],
        label_visibility="collapsed",
        help="Supported: CSV, JSON, JSONL (up to 100k candidates)",
    )

    if uploaded is not None:
        try:
            candidates_list = []

            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
                st.success(f"✅ Loaded {len(df)} candidates from CSV")
                candidates_list = _csv_to_candidates(df)

            elif uploaded.name.endswith(".json"):
                content = uploaded.read().decode("utf-8")
                data = json.loads(content)
                if isinstance(data, list):
                    candidates_list = data
                elif isinstance(data, dict) and "candidates" in data:
                    candidates_list = data["candidates"]
                else:
                    candidates_list = [data]
                st.success(f"✅ Loaded {len(candidates_list)} candidates from JSON")

            elif uploaded.name.endswith(".jsonl"):
                content = uploaded.read().decode("utf-8")
                candidates_list = [
                    json.loads(line)
                    for line in content.strip().split("\n")
                    if line.strip()
                ]
                st.success(f"✅ Loaded {len(candidates_list)} candidates from JSONL")

            if not candidates_list:
                st.warning("No candidates found in the uploaded file.")
                return None

            return _rank_and_store(candidates_list)

        except Exception as e:
            st.error(f"❌ File parsing error: {e}")
            return None

    # Show current state
    if st.session_state.get("ranking_result"):
        meta = st.session_state["ranking_result"]["metadata"]
        st.info(
            f"📊 Current ranking: {meta['candidates_ranked']} candidates ranked "
            f"in {meta['runtime_seconds']}s. Upload a new file to re-rank."
        )
    else:
        st.info("⏳ Upload a dataset or click **Try Demo Data** to get started.")

    return st.session_state.get("ranking_result")


def _load_demo_data():
    """Load sample candidates from the data directory."""
    sample_path = Path("data/sample_candidates.json")
    jsonl_path = Path("data/candidates.jsonl")

    if sample_path.exists():
        with open(sample_path) as f:
            candidates_list = json.load(f)
        if isinstance(candidates_list, dict):
            candidates_list = [candidates_list]
        st.success(f"✅ Loaded {len(candidates_list)} demo candidates")
        return _rank_and_store(candidates_list)
    elif jsonl_path.exists():
        candidates_list = []
        with open(jsonl_path) as f:
            for i, line in enumerate(f):
                if i >= 50:
                    break
                candidates_list.append(json.loads(line))
        st.success(f"✅ Loaded {len(candidates_list)} demo candidates from JSONL")
        return _rank_and_store(candidates_list)
    else:
        st.error("No demo data available (data/sample_candidates.json not found)")
        return None


def _rank_and_store(candidates_list: list):
    """Send candidates to backend for ranking and store results."""
    # Store raw candidates for other pages
    st.session_state["uploaded_candidates"] = candidates_list

    payload = {
        "candidates": candidates_list,
        "top_k": min(len(candidates_list), 500),
    }

    # Check backend availability
    if not st.session_state.get("backend_online", True):
        st.error("❌ Backend is offline. Please start the FastAPI server and retry.")
        return None

    try:
        # Progress bar for large datasets
        progress_bar = st.progress(0, text="🤖 Sending to ranking engine...")
        start_time = time.time()

        progress_bar.progress(20, text="🤖 Computing features...")
        result = rank_candidates(payload)

        elapsed = time.time() - start_time
        progress_bar.progress(100, text=f"✅ Done in {elapsed:.1f}s")
        time.sleep(0.5)
        progress_bar.empty()

        ranked = result['metadata']['candidates_ranked']
        honeypots = result['metadata']['honeypots_filtered']
        runtime = result['metadata']['runtime_seconds']

        st.success(
            f"✅ AI Ranking Completed! "
            f"**{ranked}** candidates ranked, "
            f"**{honeypots}** honeypots filtered "
            f"in **{runtime}s**"
        )

        # Store result in session state for all pages
        st.session_state["ranking_result"] = result
        st.session_state["backend_online"] = True

        return result

    except Exception as e:
        st.error(f"❌ Backend ranking failed: {e}")
        st.session_state["backend_online"] = False
        return None


def _csv_to_candidates(df: pd.DataFrame) -> list:
    """
    Convert a flat CSV DataFrame to the nested candidate structure
    expected by the backend API.
    """
    candidates = []

    for idx, row in df.iterrows():
        row_dict = row.to_dict()

        # Check if already in nested format (has candidate_id + profile)
        if "candidate_id" in row_dict and isinstance(row_dict.get("profile"), (dict, str)):
            candidate = row_dict
            for field in ["profile", "skills", "career_history", "education",
                          "certifications", "languages", "redrob_signals"]:
                if isinstance(candidate.get(field), str):
                    try:
                        candidate[field] = json.loads(candidate[field])
                    except (json.JSONDecodeError, TypeError):
                        pass
            candidates.append(candidate)
        else:
            # Flat CSV - map columns to nested structure
            candidate_id = row_dict.get(
                "candidate_id",
                row_dict.get("id", f"CAND_{idx:07d}")
            )

            candidate = {
                "candidate_id": str(candidate_id),
                "profile": {
                    "headline": str(row_dict.get("headline", row_dict.get("title", ""))),
                    "summary": str(row_dict.get("summary", "")),
                    "location": str(row_dict.get("location", "")),
                    "country": str(row_dict.get("country", "")),
                    "years_of_experience": float(
                        row_dict.get("years_of_experience",
                                     row_dict.get("experience", 0)) or 0
                    ),
                    "current_title": str(
                        row_dict.get("current_title",
                                     row_dict.get("title", ""))
                    ),
                    "current_company": str(
                        row_dict.get("current_company",
                                     row_dict.get("company", ""))
                    ),
                    "current_company_size": str(
                        row_dict.get("current_company_size", "")
                    ),
                    "current_industry": str(
                        row_dict.get("current_industry",
                                     row_dict.get("industry", ""))
                    ),
                },
                "career_history": [],
                "education": [],
                "skills": [],
                "certifications": [],
                "languages": [],
                "redrob_signals": {},
            }

            # Parse skills if present as comma-separated string or JSON
            skills_raw = row_dict.get("skills", "")
            if isinstance(skills_raw, str) and skills_raw:
                try:
                    parsed = json.loads(skills_raw)
                    if isinstance(parsed, list):
                        candidate["skills"] = parsed
                except (json.JSONDecodeError, TypeError):
                    candidate["skills"] = [
                        {"name": s.strip(), "proficiency": "intermediate",
                         "endorsements": 0, "duration_months": 12}
                        for s in skills_raw.split(",")
                        if s.strip()
                    ]

            # Parse education if present
            edu_raw = row_dict.get("education", "")
            if isinstance(edu_raw, str) and edu_raw:
                try:
                    parsed = json.loads(edu_raw)
                    if isinstance(parsed, list):
                        candidate["education"] = parsed
                except (json.JSONDecodeError, TypeError):
                    pass

            # Parse career_history if present
            career_raw = row_dict.get("career_history", "")
            if isinstance(career_raw, str) and career_raw:
                try:
                    parsed = json.loads(career_raw)
                    if isinstance(parsed, list):
                        candidate["career_history"] = parsed
                except (json.JSONDecodeError, TypeError):
                    pass

            candidates.append(candidate)

    return candidates
