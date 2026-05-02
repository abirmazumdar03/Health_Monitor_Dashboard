import streamlit as st

def render_status_bar(df):
    if df.empty:
        return
    latest = df.iloc[-1]
    is_alert = latest["meta.alert"]
    color = "red" if is_alert else "green"
    st.markdown(f"""
    <div style="height:12px;background:{color};border-radius:6px;margin-bottom:20px;"></div>
    """, unsafe_allow_html=True)