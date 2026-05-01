import streamlit as st
from pymongo import MongoClient

def get_records_by_device(device_id: str):
    uri = "mongodb+srv://abirmazumdar14798_db_user:Hswh5ndMor5m41fV@cluster0.1xkx7ny.mongodb.net/?appName=Cluster0"
    client = MongoClient(uri)
    db = client["medical_data_vault"]
    col = db["health_events"]

    cursor = col.find(
        {"meta.device_id": device_id},
        {"_id": 0}  # remove Mongo ID
    ).sort("meta.event_date", -1)

    return list(cursor)
