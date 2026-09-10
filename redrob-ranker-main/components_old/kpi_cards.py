import streamlit as st
from components.cards import metric_card

def kpi_cards():

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metric_card("👥", "Candidates", "438")

    with col2:
        metric_card("⭐", "Qualified", "72")

    with col3:
        metric_card("🏆", "Top Score", "98.7")

    with col4:
        metric_card("⚡", "Avg Score", "89.4")