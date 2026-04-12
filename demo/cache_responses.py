"""
Pre-run the three demo queries and cache responses to demo/cached_responses.json.

Usage: python demo/cache_responses.py

Run this AFTER the full pipeline is working (Neo4j loaded, Qdrant loaded).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llm.query import run_patent_query
from llm.verify import verify_citations

DEMO_QUERIES = {
    "eligibility": (
        "How has the Federal Circuit treated software patent eligibility under Alice "
        "after 2019? Which judges apply the two-step test most strictly?"
    ),
    "claim_construction": (
        "What is the CAFC standard for means-plus-function construction under "
        "35 USC 112(f)? How has it shifted since Williamson v. Citrix?"
    ),
    "obviousness": (
        "After KSR, how do NDCA district courts handle obviousness challenges "
        "to software patents with UI claim elements?"
    ),
}

OUT_FILE = Path(__file__).parent / "cached_responses.json"


def main():
    cache = {}
    if OUT_FILE.exists():
        cache = json.loads(OUT_FILE.read_text())
        print(f"Loaded {len(cache)} existing cached responses.")

    for key, question in DEMO_QUERIES.items():
        if key in cache:
            print(f"  Skipping '{key}' — already cached.")
            continue
        print(f"\n=== Caching [{key}] ===")
        print(f"  Q: {question[:80]}…")
        try:
            memo = run_patent_query(question)
            memo = verify_citations(memo)
            cache[key] = memo
            OUT_FILE.write_text(json.dumps(cache, indent=2))
            print(f"  Cached. Confidence: {memo.get('confidence')}")
        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\nDone. Cache file: {OUT_FILE}")


if __name__ == "__main__":
    main()
