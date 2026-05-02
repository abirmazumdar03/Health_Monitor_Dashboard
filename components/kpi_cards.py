import streamlit as st

def render_kpi_cards(df):
    if df.empty:
        st.warning("No data available")
        return

    latest = df.iloc[-1]

    hr = latest["vitals.heart_rate"]
    spo2 = latest["vitals.spo2"]
    is_alert = latest["meta.alert"]

    color = "#e74c3c" if is_alert else "#2ecc71"
    status = "CRITICAL" if is_alert else "NORMAL"

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(f"""
        <div style="padding:20px;border-radius:10px;background:{color};color:white;">
        <h3>❤️ Heart Rate</h3>
        <h1>{hr} BPM</h1>
        <p>Status: {status}</p>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div style="padding:20px;border-radius:10px;background:{color};color:white;">
        <h3>🩸 SpO₂</h3>
        <h1>{spo2}%</h1>
        <p>Status: {status}</p>
        </div>
        """, unsafe_allow_html=True)