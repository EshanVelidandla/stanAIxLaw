"""
Build semantic similarity edges from voyage-law-2 embeddings.
Keeps pairs with cosine similarity >= 0.80, max 15 edges per node.

Output: /data/edges/semantic_edges.csv (source_id, target_id, edge_type, weight)

Usage: python scripts/build_semantic_edges.py
"""

import csv
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = Path(__file__).parent.parent / "data"
EMB_DIR = DATA_DIR / "embeddings"
EMB_INDEX = DATA_DIR / "embeddings_index.json"
EDGES_DIR = DATA_DIR / "edges"
EDGES_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = EDGES_DIR / "semantic_edges.csv"

SIM_THRESHOLD = 0.80
MAX_EDGES_PER_NODE = 15


def main():
    if not EMB_INDEX.exists():
        print("No embeddings_index.json found — run embed_cases.py first.")
        sys.exit(1)

    index: dict[str, str] = json.loads(EMB_INDEX.read_text())
    case_ids = list(index.keys())
    print(f"Loading {len(case_ids)} embeddings…")

    embeddings = []
    valid_ids = []
    for cid in case_ids:
        path = Path(index[cid])
        if path.exists():
            embeddings.append(np.load(str(path)))
            valid_ids.append(cid)

    if not embeddings:
        print("No embedding files found.")
        sys.exit(1)

    matrix = np.vstack(embeddings)  # shape: (n, 1024)
    print(f"Computing cosine similarity for {len(valid_ids)} cases…")
    sim_matrix = cosine_similarity(matrix)  # (n, n) float32

    edges: list[tuple[str, str, float]] = []
    for i in range(len(valid_ids)):
        sims = sim_matrix[i].copy()
        sims[i] = 0.0  # exclude self
        top_indices = np.argsort(sims)[::-1]
        count = 0
        for j in top_indices:
            if count >= MAX_EDGES_PER_NODE:
                break
            w = float(sims[j])
            if w < SIM_THRESHOLD:
                break
            # Deduplicate by always storing (smaller_id, larger_id)
            a, b = valid_ids[i], valid_ids[j]
            if a > b:
                a, b = b, a
            edges.append((a, b, round(w, 4)))
            count += 1

    # Deduplicate
    unique_edges = list({(a, b): w for a, b, w in edges}.items())
    print(f"Semantic edges (threshold={SIM_THRESHOLD}): {len(unique_edges)}")

    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["source_id", "target_id", "edge_type", "weight"])
        for (a, b), w in unique_edges:
            writer.writerow([a, b, "SIMILAR_TO", w])

    print(f"Written to {OUT_CSV}")


if __name__ == "__main__":
    main()
