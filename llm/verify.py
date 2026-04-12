"""
TrustFoundry citation verification layer.
Wraps each citation in the memo with verified: true/false.
Never crashes the main pipeline.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

# TODO: Update TRUSTFOUNDRY_BASE_URL once you have the API docs
TRUSTFOUNDRY_BASE_URL = "https://api.trustfoundry.ai/v1"


def _verify_one(citation: str, holding: str) -> dict:
    """
    Call TrustFoundry to verify a citation.
    Returns {"verified": bool, "detail": str}
    """
    api_key = os.environ.get("TRUSTFOUNDRY_API_KEY", "")
    if not api_key:
        return {"verified": None, "detail": "TRUSTFOUNDRY_API_KEY not set"}

    try:
        resp = requests.post(
            f"{TRUSTFOUNDRY_BASE_URL}/verify",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"citation": citation, "holding": holding},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "verified": data.get("verified", False),
                "detail": data.get("reason") or data.get("detail") or "",
            }
        return {"verified": False, "detail": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"verified": None, "detail": str(e)}


def verify_citations(memo: dict) -> dict:
    """
    Annotate each citation in precedent_chain, cases_to_cite_for, cases_to_cite_against
    with TrustFoundry verification status.
    """
    try:
        # Annotate precedent_chain
        for entry in memo.get("precedent_chain", []):
            result = _verify_one(entry.get("citation", ""), entry.get("holding", ""))
            entry["trust_verified"] = result["verified"]
            if result["verified"] is False:
                entry["verification_warning"] = result["detail"] or "Citation not verified"

        # Annotate flat citation lists
        for key in ("cases_to_cite_for", "cases_to_cite_against"):
            memo[key] = [
                {
                    "citation": c,
                    "trust_verified": _verify_one(c, "")["verified"],
                }
                if isinstance(c, str)
                else c
                for c in memo.get(key, [])
            ]

    except Exception as e:
        memo["trust_verification"] = f"error: {e}"
        return memo

    memo["trust_verification"] = "complete"
    return memo
