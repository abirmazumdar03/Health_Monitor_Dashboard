import streamlit as st

def render_alert_banner(df):
    if df.empty:
        return
    latest = df.iloc[-1]
    if latest["meta.alert"]:
        st.toast("🚨 EMERGENCY ALERT DETECTED!", icon="🚨")
        st.error("🚨 Critical health event detected — immediate attention required.")