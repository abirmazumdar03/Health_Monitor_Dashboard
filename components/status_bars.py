import streamlit as st

def render_status_bar(df):
    latest = df.iloc[-1]
    status = latest["vitals.decision.status"]

    color = "green" if status == "NORMAL" else "red"
    st.markdown(f"""
    <div style="height:12px;background:{color};border-radius:6px;"></div>
    """, unsafe_allow_html=True)
