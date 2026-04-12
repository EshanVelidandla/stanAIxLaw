"""
Build citation edge list from case JSONs.
Output: /data/edges/citation_edges.csv (source_id, target_id, edge_type)

Usage: python scripts/build_citation_edges.py
"""

import csv
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw" / "cases"
EDGES_DIR = DATA_DIR / "edges"
EDGES_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = EDGES_DIR / "citation_edges.csv"
METADATA_CSV = DATA_DIR / "cases_metadata.csv"


def main():
    # Build set of known case IDs so we only keep in-corpus edges
    with open(METADATA_CSV) as f:
        corpus_ids = {row["case_id"] for row in csv.DictReader(f)}
    print(f"Corpus size: {len(corpus_ids)} cases")

    edges: list[tuple[str, str]] = []
    for case_path in RAW_DIR.glob("*.json"):
        case = json.loads(case_path.read_text())
        source_id = case.get("id") or case.get("case_id") or case_path.stem
        if source_id not in corpus_ids:
            continue
        citations_out = (
            case.get("citations_out")
            or case.get("citations")
            or case.get("cited_cases")
            or []
        )
        for ref in citations_out:
            # ref may be a string ID or a dict with id/case_id key
            if isinstance(ref, dict):
                target_id = ref.get("id") or ref.get("case_id") or ""
            else:
                target_id = str(ref)
            if target_id and target_id in corpus_ids and target_id != source_id:
                edges.append((source_id, target_id))

    # Deduplicate
    edges = list(set(edges))
    print(f"Citation edges (in-corpus): {len(edges)}")

    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["source_id", "target_id", "edge_type"])
        for src, tgt in edges:
            writer.writerow([src, tgt, "CITES"])

    print(f"Written to {OUT_CSV}")


if __name__ == "__main__":
    main()
