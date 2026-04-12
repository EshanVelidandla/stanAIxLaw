"""
Embed cases using voyage-law-2 and store as numpy arrays.

Usage: python scripts/embed_cases.py
"""

import csv
import json
import os
import sys
from pathlib import Path

import numpy as np
import voyageai
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

DATA_DIR = Path(__file__).parent.parent / "data"
METADATA_CSV = DATA_DIR / "cases_metadata.csv"
EMB_DIR = DATA_DIR / "embeddings"
EMB_INDEX = DATA_DIR / "embeddings_index.json"
EMB_DIR.mkdir(parents=True, exist_ok=True)

VOYAGE_MODEL = "voyage-law-2"
MAX_CHARS = 4000
BATCH_SIZE = 8


def load_text(row: dict) -> str:
    path = Path(row["full_text_path"])
    if path.exists():
        case = json.loads(path.read_text())
        text = case.get("full_text") or case.get("text") or case.get("opinion") or ""
        header = f"{row['citation_str']} ({row['court']}, {row['date_decided']})\n\n"
        return (header + text)[:MAX_CHARS]
    # Fallback: use metadata only
    return f"{row['citation_str']} {row['court']} {row['date_decided']}"


def main():
    vc = voyageai.Client(api_key=os.environ["VOYAGE_API_KEY"])

    with open(METADATA_CSV) as f:
        rows = list(csv.DictReader(f))

    existing_index: dict[str, str] = {}
    if EMB_INDEX.exists():
        existing_index = json.loads(EMB_INDEX.read_text())

    to_process = [r for r in rows if r["case_id"] not in existing_index]
    print(f"Cases to embed: {len(to_process)} (already done: {len(existing_index)})")

    for i in range(0, len(to_process), BATCH_SIZE):
        batch = to_process[i : i + BATCH_SIZE]
        texts = [load_text(r) for r in batch]
        print(f"  Embedding batch {i // BATCH_SIZE + 1}/{(len(to_process) + BATCH_SIZE - 1) // BATCH_SIZE} …")
        result = vc.embed(texts, model=VOYAGE_MODEL, input_type="document")
        for row, emb in zip(batch, result.embeddings):
            arr = np.array(emb, dtype=np.float32)
            emb_path = EMB_DIR / f"{row['case_id']}.npy"
            np.save(str(emb_path), arr)
            existing_index[row["case_id"]] = str(emb_path)

    EMB_INDEX.write_text(json.dumps(existing_index, indent=2))
    print(f"Done. Embeddings: {len(existing_index)}. Index: {EMB_INDEX}")


if __name__ == "__main__":
    main()
