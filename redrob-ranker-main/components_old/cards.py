import streamlit as st
import textwrap

def metric_card(icon, title, value, color="#00D4FF"):
    html = textwrap.dedent(f"""
    <div style="
        background:rgba(255,255,255,0.06);
        border:1px solid rgba(255,255,255,0.08);
        border-radius:18px;
        padding:20px;
        text-align:center;
        backdrop-filter:blur(10px);
        box-shadow:0 8px 25px rgba(0,0,0,.3);
        height:170px;
        display:flex;
        flex-direction:column;
        justify-content:center;
        align-items:center;
    ">

        <div style="font-size:45px;">
            {icon}
        </div>

        <h2 style="
            color:{color};
            margin:10px 0 5px 0;
            font-size:34px;
        ">
            {value}
        </h2>

        <p style="
            color:white;
            font-size:18px;
            margin:0;
        ">
            {title}
        </p>

    </div>
    """)

    st.markdown(html, unsafe_allow_html=True)