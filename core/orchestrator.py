import streamlit as st
import requests

def decrypt_records(records):
    base_url ="https://secure-e2ee-health-data-pipeline.onrender.com"
    decrypted = []

    for r in records:
        crypto_block = r.get("crypto")
        if not crypto_block:
            continue

        try:
            resp = requests.post(
                f"{base_url}/api/v1/decrypt",
                json={"crypto": crypto_block},
                timeout=10
            )
            if resp.status_code == 200:
                result = resp.json()
                result["meta"]=r.get("meta")
                decrypted.append(result)
        except Exception:
            continue

    return decrypted
