import streamlit as st
import pandas as pd

st.title("🏆 AI Candidate Leaderboard")

st.markdown("Search and shortlist the best candidates.")

search = st.text_input("🔍 Search Candidate")

score = st.slider("Minimum AI Score",50,100,80)

candidates=[

{
"name":"Alex Johnson",
"role":"Senior Backend Engineer",
"score":98.7,
"trust":99,
"exp":"5 Years",
"skills":["Python","FastAPI","AWS","Docker"]
},

{
"name":"Sarah Lee",
"role":"Machine Learning Engineer",
"score":97.4,
"trust":98,
"exp":"4 Years",
"skills":["Python","TensorFlow","LLM","PyTorch"]
},

{
"name":"David Kim",
"role":"Full Stack Engineer",
"score":96.2,
"trust":97,
"exp":"6 Years",
"skills":["React","Node","MongoDB","AWS"]
},

{
"name":"Emily Clark",
"role":"Software Engineer",
"score":94.8,
"trust":95,
"exp":"3 Years",
"skills":["Java","Spring","Docker","SQL"]
}

]

medals=["🥇","🥈","🥉","🏅"]

for i,c in enumerate(candidates):

    if search.lower() not in c["name"].lower():
        continue

    if c["score"]<score:
        continue

    with st.container(border=True):

        left,right=st.columns([4,1])

        with left:

            st.markdown(f"## {medals[i]} {c['name']}")

            st.caption(c["role"])

            s1,s2,s3=st.columns(3)

            s1.metric("Experience",c["exp"])

            s2.metric("Trust",f"{c['trust']}%")

            s3.metric("AI Score",c["score"])

            st.progress(c["score"]/100)

            cols=st.columns(len(c["skills"]))

            for idx,skill in enumerate(c["skills"]):
                cols[idx].success(skill)

        with right:

            st.button(
                "👤 View",
                key=f"view{i}",
                use_container_width=True
            )

            st.button(
                "⭐ Shortlist",
                key=f"short{i}",
                use_container_width=True
            )

            st.button(
                "📄 Resume",
                key=f"resume{i}",
                use_container_width=True
            )