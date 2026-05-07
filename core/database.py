import streamlit as st
from pymongo import MongoClient


@st.cache_resource
def _get_collection():
    client = MongoClient(
        st.secrets["MONGO_URI"],
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000,
    )
    return client["medical_data_vault"]["health_events"]

def get_records_by_device(device_id: str, limit: int = 10):
    col = _get_collection()
    cursor = col.find(
        {"meta.device_id": device_id},
        {"_id": 0}
    ).sort("meta.event_date", -1).limit(limit)
    
    return list(cursor)