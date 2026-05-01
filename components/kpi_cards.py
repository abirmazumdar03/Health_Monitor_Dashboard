import streamlit as st

def render_kpi_cards(df):
    latest = df.iloc[-1]

    hr = latest["vitals.vitals.heart_rate"]
    spo2 = latest["vitals.vitals.spo2"]
    status = latest["vitals.decision.status"]

    color = "#2ecc71" if status == "NORMAL" else "#e74c3c"

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(f"""
        <div style="padding:20px;border-radius:10px;background:{color};color:white;">
        <h3>❤️ Heart Rate</h3>
        <h1>{hr} BPM</h1>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div style="padding:20px;border-radius:10px;background:{color};color:white;">
        <h3>🩸 SpO₂</h3>
        <h1>{spo2}%</h1>
        </div>
        """, unsafe_allow_html=True)
