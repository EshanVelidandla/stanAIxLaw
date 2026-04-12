"""
Midpage API client.

Base URL:  https://app.midpage.ai/api/v1
Auth:      Authorization: Bearer {api_key}
Endpoints:
  POST /opinions/get     — fetch by ID, citation, or docket (up to 100)
  POST /opinions/search  — full-text search (assumed, same base)
"""

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://app.midpage.ai/api/v1"

RAW_DIR = Path(__file__).parent.parent / "data" / "raw" / "cases"
LOG_FILE = Path(__file__).parent.parent / "data" / "api_log.jsonl"
RAW_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def _log(method: str, url: str, status: int):
    entry = {"ts": time.time(), "method": method, "url": url, "status": status}
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _normalize(op: dict) -> dict:
    """Normalize a Midpage opinion object to our internal schema."""
    # Pick the best citation string from the citations array
    citations = op.get("citations") or []
    citation_str = citations[0]["cited_as"] if citations else op.get("case_name", "")

    return {
        "id": op.get("id", ""),
        "citation": citation_str,
        "citation_str": citation_str,
        "case_name": op.get("case_name", ""),
        "court": op.get("court_id", "") or op.get("court_abbreviation", ""),
        "date_decided": op.get("date_filed", ""),
        "judge": op.get("judge_name", ""),
        "full_text": op.get("content", "") or op.get("html_content", ""),
        "snippet": op.get("snippet", "") or op.get("case_name", ""),
        "citations_out": [],  # not returned by get endpoint — populated separately if needed
        "raw": op,
    }


class MidpageClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["MIDPAGE_API_KEY"]
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

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

    def get_by_citations(self, citation_list: list[str], include_content: bool = False) -> list[dict]:
        """
        Fetch opinions by citation strings (up to 100 at a time).
        Returns normalized list of case dicts.
        """
        data = self._post("/opinions/get", {
            "citations": citation_list,
            "include_content": include_content,
        })
        return [_normalize(op) for op in data.get("opinions", [])]

    def get_by_ids(self, opinion_ids: list[str], include_content: bool = True) -> list[dict]:
        """Fetch opinions by ID (up to 100). Returns normalized list."""
        data = self._post("/opinions/get", {
            "opinion_ids": opinion_ids,
            "include_content": include_content,
        })
        return [_normalize(op) for op in data.get("opinions", [])]

    def get_case(self, case_id: str) -> dict:
        """Fetch a single opinion by ID with full content. Cached locally."""
        cache_path = RAW_DIR / f"{case_id}.json"
        if cache_path.exists():
            return json.loads(cache_path.read_text())
        results = self.get_by_ids([case_id], include_content=True)
        if not results:
            raise ValueError(f"Opinion not found: {case_id}")
        data = results[0]
        cache_path.write_text(json.dumps(data, indent=2))
        return data

    def search_by_citation(self, citation_str: str) -> dict | None:
        """Look up a single case by citation string."""
        results = self.get_by_citations([citation_str], include_content=False)
        return results[0] if results else None

    def search(self, query: str, jurisdiction: str = "cafc", date_after: str = "2005-01-01", limit: int = 50) -> list[dict]:
        """
        Full-text search. Uses /opinions/search if available,
        otherwise falls back to citation lookup with the query string.
        """
        try:
            data = self._post("/opinions/search", {
                "q": query,
                "court_id": jurisdiction,
                "limit": limit,
            })
            opinions = data.get("opinions") or data.get("results") or data.get("hits") or []
            return [_normalize(op) for op in opinions]
        except Exception:
            # Fallback: treat query as a citation string
            result = self.search_by_citation(query)
            return [result] if result else []

    def get_citations(self, case_id: str) -> list[str]:
        """Return outgoing citation IDs for a case (not supported by get endpoint — returns [])."""
        case = self.get_case(case_id)
        return case.get("citations_out") or []


# ── Smoke test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    client = MidpageClient()
    print(f"API key: {client.api_key[:12]}…\n")

    print("Fetching Alice Corp (573 U.S. 208) by citation…")
    result = client.search_by_citation("573 U.S. 208")
    if result:
        print(f"  ✓ Found: {result['case_name']}")
        print(f"    citation:  {result['citation']}")
        print(f"    court:     {result['court']}")
        print(f"    date:      {result['date_decided']}")
        print(f"    judge:     {result['judge']}")
        print(f"    has text:  {bool(result['full_text'])}")
        print(f"\n  Raw keys: {list(result['raw'].keys())}")
    else:
        print("  ✗ Not found — check API key or endpoint")
        import sys; sys.exit(1)

    print("\nSmoke test passed.")
