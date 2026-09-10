import streamlit as st

def upload_section():

    st.markdown("""
    <div style="
        background:rgba(255,255,255,0.05);
        border:1px solid rgba(255,255,255,0.08);
        border-radius:25px;
        padding:35px;
        margin-top:20px;
        margin-bottom:30px;
        backdrop-filter:blur(15px);
        box-shadow:0px 10px 35px rgba(0,0,0,.35);
    ">

        <h2 style="text-align:center;color:white;">
            📂 Upload Candidate Dataset
        </h2>

        <p style="
            text-align:center;
            color:#AAB6C5;
            font-size:18px;
        ">
        Upload JSONL or CSV files to start AI-powered candidate ranking
        </p>

    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload Candidate Dataset",
        type=["jsonl", "csv"],
        label_visibility="collapsed",
    )

    if uploaded:
        st.success(f"✅ {uploaded.name} uploaded successfully!")

    return uploaded