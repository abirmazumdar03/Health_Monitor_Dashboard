from typing import List, Optional

import requests


def _normalize_base_url(base_url: str) -> str:
    return (base_url or "").strip().rstrip("/")


def _crypto_from_record(record: dict):
    """Resolve encrypted payload from common ingest / vault shapes."""
    if not isinstance(record, dict):
        return None
    c = record.get("crypto")
    if c:
        return c
    for key in ("ciphertext", "encrypted_payload", "payload_enc"):
        if record.get(key) is not None:
            return record
    inner = record.get("data") or record.get("payload") or record.get("body")
    if isinstance(inner, dict):
        c = inner.get("crypto")
        if c:
            return c
    return None


def decrypt_records(
    records,
    base_url: str,
    debug_hints: Optional[List[str]] = None,
    timeout_sec: int = 8,
):
    base = _normalize_base_url(base_url)
    decrypted = []
    saw_crypto = False

    consecutive_failures = 0

    for r in records[:10]:
        crypto_block = _crypto_from_record(r)
        if not crypto_block:
            continue
        saw_crypto = True

        try:
            resp = requests.post(
                f"{base}/api/v1/decrypt",
                json={"crypto": crypto_block},
                timeout=timeout_sec,
            )

            if resp.status_code == 200:
                result = resp.json()
                result["meta"] = r.get("meta", {})
                decrypted.append(result)
                consecutive_failures = 0
            elif debug_hints is not None and len(debug_hints) < 3:
                snippet = (resp.text or "")[:400].replace("\n", " ")
                debug_hints.append(f"HTTP {resp.status_code} from {base}/api/v1/decrypt — {snippet}")
                consecutive_failures += 1

                # Some backends expect raw crypto block without wrapper.
                if isinstance(crypto_block, dict):
                    retry = requests.post(
                        f"{base}/api/v1/decrypt",
                        json=crypto_block,
                        timeout=timeout_sec,
                    )
                    if retry.status_code == 200:
                        result = retry.json()
                        result["meta"] = r.get("meta", {})
                        decrypted.append(result)
                        consecutive_failures = 0

        except Exception as ex:
            if debug_hints is not None and len(debug_hints) < 3:
                debug_hints.append(f"Request error: {ex!s}")
            consecutive_failures += 1

        # Avoid long blocking when decrypt service is unavailable.
        if consecutive_failures >= 3 and not decrypted:
            break

    if debug_hints is not None and not saw_crypto:
        debug_hints.append(
            "No `crypto` (or compatible) field found on fetched Mongo documents."
        )

    return decrypted
