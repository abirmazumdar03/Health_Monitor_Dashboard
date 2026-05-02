import streamlit as st
import pandas as pd
import hashlib
import json
import concurrent.futures
from streamlit_autorefresh import st_autorefresh
from core.database import get_records_by_device
from core.orchestrator import decrypt_records
from utils.data_cleaner import clean_timestamps
from utils.chart_engine import plot_synced_vitals
from components.kpi_cards import render_kpi_cards
from components.status_bars import render_status_bar
from components.alerts import render_alert_banner

st.set_page_config(page_title="Secure Medical Dashboard", layout="wide")


def _records_fingerprint(records):
    """Build a stable hash to detect whether encrypted payload changed."""
    try:
        payload = json.dumps(records, sort_keys=True, default=str)
    except TypeError:
        payload = str(records)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _get_executor() -> concurrent.futures.ThreadPoolExecutor:
    ex = st.session_state.get("_decrypt_executor")
    if ex is None:
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        st.session_state["_decrypt_executor"] = ex
    return ex

# Auto-refresh every 10 seconds
st_autorefresh(interval=10_000, key="data_refresh")

st.title("🩺 Secure Medical Monitoring Dashboard")

# ---------- Sidebar ----------
st.sidebar.header("Filters")
device_id = st.sidebar.text_input("Enter Device ID", value="pi-edge-001")
time_window = st.sidebar.slider("Time window (last minutes)", 10, 240, 60)

# ---------- Fetch ----------
raw_records = get_records_by_device(device_id, limit=10)

if not raw_records:
    st.warning("No records found for this device.")
    st.stop()

# ---------- Decrypt ----------
current_fp = _records_fingerprint(raw_records)
base_url = st.secrets["FLASK_SERVER_URL"].strip().rstrip("/")

decrypt_future = st.session_state.get("decrypt_future")
decrypt_target_fp = st.session_state.get("decrypt_target_fp")

# Promote completed background decrypt before deciding what to show
if decrypt_future is not None and decrypt_future.done():
    try:
        new_decrypted = decrypt_future.result()
    except Exception:
        new_decrypted = []

    if new_decrypted:
        st.session_state["records_fp"] = decrypt_target_fp
        st.session_state["decrypted_records"] = new_decrypted

    st.session_state["decrypt_future"] = None
    st.session_state["decrypt_target_fp"] = None
    decrypt_future = None

decrypted_records = st.session_state.get("decrypted_records")
cached_fp = st.session_state.get("records_fp")

# First load (or cleared session): decrypt synchronously so we never show
# "Security Redacted" while a background job is still running.
if not decrypted_records:
    _hints = []
    decrypted_records = decrypt_records(
        raw_records, base_url, debug_hints=_hints, timeout_sec=8
    )
    if decrypted_records:
        st.session_state["records_fp"] = current_fp
        st.session_state["decrypted_records"] = decrypted_records
    else:
        st.error("🔒 Security Redacted — No valid decrypted data available.")
        with st.expander("Troubleshooting"):
            st.markdown(
                "- Set **FLASK_SERVER_URL** in Streamlit secrets to the **same origin** as ingest "
                "(e.g. `https://secure-e2ee-health-data-pipeline.onrender.com` — no trailing slash).\n"
                "- Decrypt endpoint must return **200** for `POST /api/v1/decrypt`.\n"
                "- Mongo documents need a **crypto** (or compatible) field on each record."
            )
            for h in _hints:
                st.caption(h)
        st.stop()

cached_fp = st.session_state.get("records_fp")

# New encrypted payload while we already have charts: refresh in background, keep showing last good data
decrypt_future = st.session_state.get("decrypt_future")
decrypt_target_fp = st.session_state.get("decrypt_target_fp")
if cached_fp != current_fp:
    already_running_same_batch = (
        decrypt_future is not None
        and not decrypt_future.done()
        and decrypt_target_fp == current_fp
    )
    if not already_running_same_batch:
        ex = _get_executor()
        st.session_state["decrypt_future"] = ex.submit(
            decrypt_records, raw_records, base_url, None, 8
        )
        st.session_state["decrypt_target_fp"] = current_fp
        decrypt_future = st.session_state["decrypt_future"]

decrypted_records = st.session_state["decrypted_records"]

if cached_fp == current_fp:
    st.caption("Charts live; encrypted payload unchanged since last decrypt.")
elif decrypt_future is not None and not decrypt_future.done():
    st.caption("New data ingested — decrypting in background; charts show last decrypted batch.")

# ---------- Build DataFrame ----------
df = pd.json_normalize(decrypted_records, sep='.')
df = clean_timestamps(df)

# ---------- Time filter ----------
if "meta.event_date" in df.columns and not df.empty:
    latest_time = df["meta.event_date"].max()
    cutoff = latest_time - pd.Timedelta(minutes=time_window)
    df = df[df["meta.event_date"] >= cutoff]

if df.empty:
    st.warning("No data in selected time window.")
    st.stop()

# ---------- UI ----------
render_alert_banner(df)
render_kpi_cards(df)
render_status_bar(df)

st.markdown("## 📈 Chronological Pulse (Synced Trends)")
plot_synced_vitals(df)