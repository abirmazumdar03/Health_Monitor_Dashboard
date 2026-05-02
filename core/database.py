import streamlit as st
from pymongo import MongoClient

"""def get_records_by_device(device_id: str):
    uri = "mongodb://abirmazumdar14798_db_user:PI1234@ac-8i8t1do-shard-00-00.2awuqsz.mongodb.net:27017,ac-8i8t1do-shard-00-01.2awuqsz.mongodb.net:27017,ac-8i8t1do-shard-00-02.2awuqsz.mongodb.net:27017/?ssl=true&replicaSet=atlas-gjt5jw-shard-0&authSource=admin&appName=Cluster0"
    client = MongoClient(uri)
    db = client["medical_data_vault"]
    col = db["health_events"]

    cursor = col.find(
        {"meta.device_id": device_id},
        {"_id": 0}  # remove Mongo ID
    ).sort("meta.event_date", -1)

    return list(cursor)"""


#import streamlit as st
#from pymongo import MongoClient

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