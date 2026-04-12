"""
Midpage API client — primary case law source.

NOTE: Fill in BASE_URL and AUTH_HEADER once you've read the API docs at
https://bit.ly/4caSNXS and obtained your API key.

Run this file directly to test: python scripts/midpage_client.py
"""

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# ── Update these once you've read the Midpage API docs ───────────────────────
BASE_URL = "https://api.midpage.ai/v1"          # confirm from docs
AUTH_HEADER_NAME = "X-Api-Key"                   # confirm from docs (may be "Authorization: Bearer ...")
# ─────────────────────────────────────────────────────────────────────────────

RAW_DIR = Path(__file__).parent.parent / "data" / "raw" / "cases"
LOG_FILE = Path(__file__).parent.parent / "data" / "api_log.jsonl"
RAW_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def _log(method: str, url: str, status: int, note: str = ""):
    entry = {"ts": time.time(), "method": method, "url": url, "status": status, "note": note}
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


class MidpageClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["MIDPAGE_API_KEY"]
        self.session = requests.Session()
        self.session.headers.update({
            AUTH_HEADER_NAME: self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _get(self, path: str, params: dict | None = None, retries: int = 4) -> dict:
        url = f"{BASE_URL}/{path.lstrip('/')}"
        backoff = 2
        for attempt in range(retries):
            resp = self.session.get(url, params=params)
            _log("GET", url, resp.status_code)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                wait = backoff ** attempt
                print(f"  Rate limited — sleeping {wait}s")
                time.sleep(wait)
                continue
            resp.raise_for_status()
        raise RuntimeError(f"Failed after {retries} attempts: {url}")

    def _post(self, path: str, body: dict, retries: int = 4) -> dict:
        url = f"{BASE_URL}/{path.lstrip('/')}"
        backoff = 2
        for attempt in range(retries):
            resp = self.session.post(url, json=body)
            _log("POST", url, resp.status_code)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                wait = backoff ** attempt
                print(f"  Rate limited — sleeping {wait}s")
                time.sleep(wait)
                continue
            resp.raise_for_status()
        raise RuntimeError(f"Failed after {retries} attempts: {url}")

    # ── Public API ────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        jurisdiction: str = "cafc",
        date_after: str = "2005-01-01",
        limit: int = 50,
    ) -> list[dict]:
        """
        Returns list of case metadata dicts.
        Expected response keys (adjust to actual schema):
          id, citation, court, date_decided, snippet
        """
        # TODO: confirm endpoint path + param names from API docs
        data = self._get(
            "/search",
            params={
                "q": query,
                "jurisdiction": jurisdiction,
                "date_after": date_after,
                "limit": limit,
            },
        )
        # Adapt to actual response structure — common patterns:
        #   data["results"], data["cases"], data["hits"], data (if list)
        results = data.get("results") or data.get("cases") or data.get("hits") or data
        return results if isinstance(results, list) else []

    def get_case(self, case_id: str) -> dict:
        """
        Returns full case dict with at minimum:
          id, citation, court, date_decided, full_text, citations_out[]
        Caches raw response to /data/raw/cases/{case_id}.json
        """
        cache_path = RAW_DIR / f"{case_id}.json"
        if cache_path.exists():
            return json.loads(cache_path.read_text())

        # TODO: confirm endpoint path from API docs (may be /cases/{id} or /opinion/{id})
        data = self._get(f"/cases/{case_id}")
        cache_path.write_text(json.dumps(data, indent=2))
        return data

    def get_citations(self, case_id: str) -> list[str]:
        """
        Returns list of case IDs that this case cites.
        If Midpage has a dedicated citations endpoint, use it.
        Otherwise extract from the full case's citations_out field.
        """
        # TODO: confirm whether there's a dedicated /cases/{id}/citations endpoint
        case = self.get_case(case_id)
        return case.get("citations_out") or case.get("citations") or []

    def search_by_citation(self, citation_str: str) -> dict | None:
        """
        Look up a case by its citation string (e.g. "573 U.S. 208").
        Returns the first matching case or None.
        """
        results = self.search(citation_str, jurisdiction="all", limit=3)
        return results[0] if results else None


# ── Smoke test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    client = MidpageClient()

    print("Testing search: 'Alice Corp patent eligibility' …")
    try:
        results = client.search("Alice Corp patent eligibility", jurisdiction="cafc", limit=3)
        print(f"  Got {len(results)} results")
        if results:
            print(f"  First result keys: {list(results[0].keys())}")
            print(f"  First result: {json.dumps(results[0], indent=2)[:500]}")
    except Exception as e:
        print(f"  SEARCH FAILED: {e}", file=sys.stderr)
        print("  -> Check BASE_URL, AUTH_HEADER_NAME, and your MIDPAGE_API_KEY in .env")
        sys.exit(1)

    if results:
        case_id = results[0].get("id") or results[0].get("case_id")
        if case_id:
            print(f"\nFetching case {case_id} …")
            try:
                case = client.get_case(case_id)
                print(f"  Case keys: {list(case.keys())}")
                print(f"  citations_out count: {len(client.get_citations(case_id))}")
            except Exception as e:
                print(f"  CASE FETCH FAILED: {e}", file=sys.stderr)

    print("\nSmoke test done.")
