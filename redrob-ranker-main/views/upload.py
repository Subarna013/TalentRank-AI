import streamlit as st
import pandas as pd
import json
import time
from pathlib import Path
from utils.api_client import rank_candidates


# ─── Helper Functions (defined before use) ───


def render():
    def _do_ranking(candidates_list):
        """Send candidates to backend and store results."""
        st.session_state["uploaded_candidates"] = candidates_list

        payload = {
            "candidates": candidates_list,
            "top_k": min(len(candidates_list), 500),
        }

        if not st.session_state.get("backend_online", True):
            st.error("❌ Backend is offline. Start the FastAPI server first.")
            return

        try:
            progress = st.progress(0, text="🤖 Initializing ranking engine...")
            progress.progress(10, text="📊 Computing features for candidates...")

            start = time.time()
            result = rank_candidates(payload)
            elapsed = time.time() - start

            progress.progress(100, text="✅ Complete!")
            time.sleep(0.3)
            progress.empty()

            meta = result["metadata"]

            st.session_state["ranking_result"] = result
            st.session_state["backend_online"] = True

            # Success message
            st.balloons()

            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            col_r1.metric("Candidates Ranked", meta["candidates_ranked"])
            col_r2.metric("Honeypots Filtered", meta["honeypots_filtered"])
            col_r3.metric("Processing Time", f"{meta['runtime_seconds']}s")
            col_r4.metric("Top Score", f"{result['results'][0]['score']*100:.1f}" if result['results'] else "—")

            st.success(
                f"🚀 **Ranking complete!** Navigate to Dashboard, Rankings, or Candidates to explore results."
            )

            with st.expander("📋 View Raw Response"):
                st.json(result)

        except Exception as e:
            st.error(f"❌ Ranking failed: {e}")
            st.session_state["backend_online"] = False


    def _csv_to_candidates(df):
        """Convert CSV DataFrame to candidate list."""
        candidates = []
        for idx, row in df.iterrows():
            row_dict = row.to_dict()

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
                candidate_id = row_dict.get("candidate_id", row_dict.get("id", f"CAND_{idx:07d}"))
                candidate = {
                    "candidate_id": str(candidate_id),
                    "profile": {
                        "headline": str(row_dict.get("headline", row_dict.get("title", ""))),
                        "summary": str(row_dict.get("summary", "")),
                        "location": str(row_dict.get("location", "")),
                        "country": str(row_dict.get("country", "")),
                        "years_of_experience": float(row_dict.get("years_of_experience", row_dict.get("experience", 0)) or 0),
                        "current_title": str(row_dict.get("current_title", row_dict.get("title", ""))),
                        "current_company": str(row_dict.get("current_company", row_dict.get("company", ""))),
                        "current_company_size": str(row_dict.get("current_company_size", "")),
                        "current_industry": str(row_dict.get("current_industry", row_dict.get("industry", ""))),
                    },
                    "career_history": [],
                    "education": [],
                    "skills": [],
                    "certifications": [],
                    "languages": [],
                    "redrob_signals": {},
                }
                skills_raw = row_dict.get("skills", "")
                if isinstance(skills_raw, str) and skills_raw:
                    try:
                        parsed = json.loads(skills_raw)
                        if isinstance(parsed, list):
                            candidate["skills"] = parsed
                    except (json.JSONDecodeError, TypeError):
                        candidate["skills"] = [
                            {"name": s.strip(), "proficiency": "intermediate", "endorsements": 0, "duration_months": 12}
                            for s in skills_raw.split(",") if s.strip()
                        ]
                candidates.append(candidate)
        return candidates


    # ─── Page Content ───

    st.markdown("""
    <div class="welcome-header">
        <div class="welcome-text">
            <h2>📤 Upload Resumes</h2>
            <p>Upload candidate datasets to run AI-powered ranking and analysis.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ─── Upload Area ───
    col_main, col_info = st.columns([2, 1])

    with col_main:
        st.markdown("### Choose your file")
        st.caption("Supported formats: CSV, JSON, JSONL — up to 100,000 candidates")

        uploaded = st.file_uploader(
            "Drop your file here",
            type=["csv", "json", "jsonl"],
            help="CSV (flat or nested), JSON (array or object), JSONL (one candidate per line)",
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # Demo button
        demo_col1, demo_col2 = st.columns([1, 2])
        with demo_col1:
            demo_clicked = st.button("🚀 Load Demo Data", use_container_width=True)
        with demo_col2:
            st.caption("Load 50 sample candidates to test the system instantly")

    with col_info:
        st.markdown("### 📋 File Format Guide")

        with st.expander("JSON / JSONL Format", expanded=True):
            st.code("""{
      "candidate_id": "CAND_001",
      "profile": {
        "headline": "ML Engineer",
        "location": "Bangalore",
        "country": "India",
        "years_of_experience": 6.0,
        "current_title": "Senior ML Engineer",
        "current_company": "Startup Inc"
      },
      "skills": [{"name": "Python", "proficiency": "advanced"}],
      "career_history": [...],
      "education": [...],
      "redrob_signals": {...}
    }""", language="json")

        with st.expander("CSV Format"):
            st.write("Flat CSV with columns:")
            st.code("candidate_id, title, company, location, country, years_of_experience, skills", language="text")

        # Current session status
        result = st.session_state.get("ranking_result")
        if result:
            meta = result["metadata"]
            st.markdown("### 📊 Current Session")
            st.metric("Candidates Ranked", meta.get("candidates_ranked", 0))
            st.metric("Processing Time", f"{meta.get('runtime_seconds', 0)}s")

    st.divider()

    # ─── Handle Upload ───
    if demo_clicked:
        sample_path = Path("data/sample_candidates.json")
        jsonl_path = Path("data/candidates.jsonl")

        if sample_path.exists():
            with open(sample_path) as f:
                candidates_list = json.load(f)
            if isinstance(candidates_list, dict):
                candidates_list = [candidates_list]
            st.success(f"✅ Loaded {len(candidates_list)} demo candidates")
            _do_ranking(candidates_list)
        elif jsonl_path.exists():
            candidates_list = []
            with open(jsonl_path) as f:
                for i, line in enumerate(f):
                    if i >= 50:
                        break
                    candidates_list.append(json.loads(line))
            st.success(f"✅ Loaded {len(candidates_list)} demo candidates from JSONL")
            _do_ranking(candidates_list)
        else:
            st.error("No demo data found.")

    elif uploaded is not None:
        try:
            candidates_list = []

            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
                st.success(f"✅ Parsed {len(df)} rows from CSV")
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
                st.success(f"✅ Parsed {len(candidates_list)} candidates from JSON")

            elif uploaded.name.endswith(".jsonl"):
                content = uploaded.read().decode("utf-8")
                candidates_list = [
                    json.loads(line) for line in content.strip().split("\n") if line.strip()
                ]
                st.success(f"✅ Parsed {len(candidates_list)} candidates from JSONL")

            if candidates_list:
                _do_ranking(candidates_list)
            else:
                st.warning("No candidates found in file.")

        except Exception as e:
            st.error(f"❌ File parsing error: {e}")
