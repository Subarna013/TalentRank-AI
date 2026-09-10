import streamlit as st

def hero():

    st.markdown("""
    <div style="
        text-align:center;
        padding:40px 0 20px 0;
    ">

    <h1 style="
        font-size:70px;
        font-weight:900;
        margin-bottom:10px;
        background:linear-gradient(90deg,#00D4FF,#6C63FF,#00FFA3);
        -webkit-background-clip:text;
        -webkit-text-fill-color:transparent;
    ">
    🚀 REDROB AI
    </h1>

    <h3 style="
        color:#D1D5DB;
        font-weight:400;
    ">
    Next Generation Candidate Intelligence Platform
    </h3>

    <p style="
        color:#94A3B8;
        font-size:20px;
        margin-top:15px;
    ">
    Rank • Compare • Explain • Hire
    </p>

    </div>
    """, unsafe_allow_html=True)