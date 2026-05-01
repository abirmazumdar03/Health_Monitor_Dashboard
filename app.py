import streamlit as st
import pandas as pd
from core.database import get_records_by_device
from core.orchestrator import decrypt_records
from utils.data_cleaner import clean_timestamps
from utils.chart_engine import plot_synced_vitals
from components.kpi_cards import render_kpi_cards
from components.status_bars import render_status_bar
from components.alerts import render_alert_banner

st.set_page_config(page_title="Secure Medical Dashboard", layout="wide")

st.title("🩺 Secure Medical Monitoring Dashboard")

# ---------- Sidebar ----------
st.sidebar.header("Filters")
device_id = st.sidebar.text_input("Enter Device ID", value="pi-edge-001")
time_window = st.sidebar.slider("Time window (last minutes)", 10, 240, 60)

# ---------- Data Fetch ----------
with st.spinner("Fetching encrypted records from MongoDB..."):
    raw_records = get_records_by_device(device_id)

if not raw_records:
    st.warning("No records found for this device.")
    st.stop()


#"""print("\n--------------- RAW RECORDS ---------------")
#print(type(raw_records))
#print(raw_records)
#for rec in raw_records:
#    print(rec)
#print("--------------- END OF RAW RECORDS ---------------\n")"""

# ---------- Decrypt via Flask ----------
with st.spinner("🔐 Decrypting records via Flask..."):
    decrypted_records = decrypt_records(raw_records)

if not decrypted_records:
    st.error("🔒 Security Redacted — No valid decrypted data available.")
    st.stop()


print("\n--------------- DECRYPT RECORDS ---------------")
print(type(decrypted_records))
print(decrypted_records)
for rec in decrypted_records:
    print(rec)
print("--------------- END OF DECRYPT RECORDS ---------------\n")


# ---------- Clean timestamps ----------
df = clean_timestamps(pd.json_normalize(decrypted_records))


print("\n--------------- DF RECORDS ---------------")
print(type(df))
print(df.columns)
print(df)
print("--------------- END OF DF RECORDS ---------------\n")


# Filter by time window
latest_time = df["meta.event_date"].max()
cutoff = latest_time - pd.Timedelta(minutes=time_window)
df = df[df["meta.event_date"] >= cutoff]

if df.empty:
    st.warning("No data in selected time window.")
    st.stop()

# ---------- UI Layout ----------
render_alert_banner(df)
render_kpi_cards(df)
render_status_bar(df)

st.markdown("## 📈 Chronological Pulse (Synced Trends)")
plot_synced_vitals(df)
