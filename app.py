import streamlit as st
import pandas as pd
import hashlib
import json
import concurrent.futures
from datetime import datetime, timezone

import requests
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

st.title("🩺 Secure Medical Monitoring Dashboard")

# ---------- Sidebar ----------
st.sidebar.header("Filters")
device_id = st.sidebar.text_input("Enter Device ID", value="pi-edge-001")
time_window = st.sidebar.slider("Time window (last minutes)", 10, 240, 60)
refresh_sec = st.sidebar.slider("Refresh interval (seconds)", 2, 30, 5)
max_points = st.sidebar.slider("Max points to plot", 20, 500, 200, step=10)

# Auto-refresh
st_autorefresh(interval=refresh_sec * 1000, key="data_refresh")

# ---------- Fetch ----------
mongo_ok = True
mongo_error = None
try:
    raw_records = get_records_by_device(device_id, limit=max_points)
except Exception as ex:
    mongo_ok = False
    mongo_error = str(ex)
    raw_records = []

if not raw_records:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Mongo", "❌" if not mongo_ok else "✅")
    with c2:
        st.metric("Decrypt API", "—")
    with c3:
        st.metric("Last ingest", "—")
    with c4:
        st.metric("Last decrypt", "—")

    if not mongo_ok:
        st.error("Mongo fetch failed.")
        st.caption(mongo_error)
    else:
        st.warning("No records found for this device.")
    st.stop()

# ---------- Decrypt ----------
current_fp = _records_fingerprint(raw_records)
base_url = st.secrets["FLASK_SERVER_URL"].strip().rstrip("/")

decrypt_future = st.session_state.get("decrypt_future")
decrypt_target_fp = st.session_state.get("decrypt_target_fp")

# ---------- Health probes (fast, non-blocking) ----------
decrypt_api_ok = None
decrypt_api_error = None
try:
    r = requests.get(base_url, timeout=2)
    decrypt_api_ok = 200 <= r.status_code < 500
except Exception as ex:
    decrypt_api_ok = False
    decrypt_api_error = str(ex)

last_decrypt_at = st.session_state.get("last_decrypt_at")
last_ingest_at = None
try:
    # raw is sorted desc by event_date
    last_ingest_at = raw_records[0].get("meta", {}).get("event_date")
except Exception:
    last_ingest_at = None

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Mongo", "✅" if mongo_ok else "❌")
with c2:
    st.metric("Decrypt API", "✅" if decrypt_api_ok else "❌")
with c3:
    st.metric("Last ingest", str(last_ingest_at) if last_ingest_at else "—")
with c4:
    st.metric("Last decrypt", last_decrypt_at if last_decrypt_at else "—")

if decrypt_api_ok is False and decrypt_api_error:
    st.caption(f"Decrypt API probe: {decrypt_api_error}")

# Promote completed background decrypt before deciding what to show
if decrypt_future is not None and decrypt_future.done():
    try:
        new_decrypted = decrypt_future.result()
    except Exception:
        new_decrypted = []

    if new_decrypted:
        st.session_state["records_fp"] = decrypt_target_fp
        st.session_state["decrypted_records"] = new_decrypted
        st.session_state["last_decrypt_at"] = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")

    st.session_state["decrypt_future"] = None
    st.session_state["decrypt_target_fp"] = None
    decrypt_future = None

decrypted_records = st.session_state.get("decrypted_records")
cached_fp = st.session_state.get("records_fp")

# First load: start decrypt in background and keep UI responsive.
if not decrypted_records:
    if decrypt_future is None:
        ex = _get_executor()
        st.session_state["decrypt_future"] = ex.submit(
            decrypt_records, raw_records, base_url, [], 8
        )
        st.session_state["decrypt_target_fp"] = current_fp
        decrypt_future = st.session_state["decrypt_future"]
        decrypt_target_fp = st.session_state["decrypt_target_fp"]

    # If still running, show status and wait for next refresh tick.
    if decrypt_future is not None and not decrypt_future.done():
        st.info("Decrypting initial payload… charts will appear automatically.")
        st.stop()

    # Finished but produced nothing: show troubleshooting.
    _hints = []
    try:
        maybe = decrypt_future.result() if decrypt_future is not None else []
    except Exception:
        maybe = []

    st.session_state["decrypt_future"] = None
    st.session_state["decrypt_target_fp"] = None
    decrypt_future = None

    if maybe:
        st.session_state["records_fp"] = current_fp
        st.session_state["decrypted_records"] = maybe
        st.session_state["last_decrypt_at"] = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
        decrypted_records = maybe
        cached_fp = current_fp
    else:
        st.error("🔒 Security Redacted — No valid decrypted data available.")
        with st.expander("Troubleshooting"):
            st.markdown(
                "- Set **FLASK_SERVER_URL** in Streamlit secrets to the **same origin** as ingest "
                "(e.g. `https://secure-e2ee-health-data-pipeline.onrender.com` — no trailing slash).\n"
                "- Decrypt endpoint must return **200** for `POST /api/v1/decrypt`.\n"
                "- Mongo documents need a **crypto** (or compatible) field on each record."
            )
            # Re-run once with hints so we can show actionable errors
            debug_hints = []
            _ = decrypt_records(raw_records, base_url, debug_hints=debug_hints, timeout_sec=8)
            for h in debug_hints:
                st.caption(h)
        st.stop()

cached_fp = st.session_state.get("records_fp")

# New encrypted payload while we already have charts: refresh in background, keep showing last good data
decrypt_future = st.session_state.get("decrypt_future")
decrypt_target_fp = st.session_state.get("decrypt_target_fp")
if cached_fp != current_fp:
    # If a decrypt is already running, don't replace it.
    # Keep the newest payload fingerprint queued for next refresh cycle.
    if decrypt_future is not None and not decrypt_future.done():
        st.session_state["pending_fp"] = current_fp
    else:
        ex = _get_executor()
        st.session_state["decrypt_future"] = ex.submit(
            decrypt_records, raw_records, base_url, None, 8
        )
        st.session_state["decrypt_target_fp"] = current_fp
        decrypt_future = st.session_state["decrypt_future"]
        st.session_state["pending_fp"] = None

decrypted_records = st.session_state["decrypted_records"]

if cached_fp == current_fp:
    st.caption("Charts live; encrypted payload unchanged since last decrypt.")
elif decrypt_future is not None and not decrypt_future.done():
    pending_fp = st.session_state.get("pending_fp")
    if pending_fp:
        st.caption("New data keeps arriving — decrypt queue active; charts update as jobs complete.")
    else:
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