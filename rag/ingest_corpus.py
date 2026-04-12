"""
Ingest statutory documents (MPEP, 35 USC, 37 CFR) into Qdrant.

Usage: python rag/ingest_corpus.py

Documents are chunked (512 tokens, 64-token overlap) and embedded with
voyage-law-2 before upsertion into the "patent_statutes" Qdrant collection.
"""

import hashlib
import os
import sys
from pathlib import Path

import tiktoken
import voyageai
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
PARSED_DIR = DATA_DIR / "parsed_docs"
PARSED_DIR.mkdir(parents=True, exist_ok=True)

COLLECTION = "patent_statutes"
VOYAGE_MODEL = "voyage-law-2"
CHUNK_TOKENS = 512
OVERLAP_TOKENS = 64
EMB_DIM = 1024
BATCH_SIZE = 8

tokenizer = tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str, source: str, section: str) -> list[dict]:
    tokens = tokenizer.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + CHUNK_TOKENS, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = tokenizer.decode(chunk_tokens)
        chunks.append({
            "text": chunk_text,
            "source": source,
            "section": section,
            "chunk_index": len(chunks),
        })
        start += CHUNK_TOKENS - OVERLAP_TOKENS
    return chunks


def ingest_markdown_file(path: Path, source: str, section: str, vc, qc) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    chunks = chunk_text(text, source, section)
    print(f"  {path.name}: {len(chunks)} chunks")

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i: i + BATCH_SIZE]
        texts = [c["text"] for c in batch]
        result = vc.embed(texts, model=VOYAGE_MODEL, input_type="document")
        points = []
        for chunk, emb in zip(batch, result.embeddings):
            uid = hashlib.md5(f"{source}{section}{chunk['chunk_index']}".encode()).hexdigest()
            uid_int = int(uid[:16], 16)
            points.append(PointStruct(
                id=uid_int,
                vector=emb,
                payload={
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "section": chunk["section"],
                    "chunk_index": chunk["chunk_index"],
                },
            ))
        qc.upsert(collection_name=COLLECTION, points=points)

    return len(chunks)


def setup_collection(qc):
    existing = [c.name for c in qc.get_collections().collections]
    if COLLECTION not in existing:
        qc.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=EMB_DIM, distance=Distance.COSINE),
        )
        print(f"Created Qdrant collection: {COLLECTION}")
    else:
        print(f"Collection '{COLLECTION}' already exists.")


def main():
    vc = voyageai.Client(api_key=os.environ["VOYAGE_API_KEY"])
    qc = QdrantClient(
        url=os.environ["QDRANT_URL"],
        api_key=os.environ.get("QDRANT_API_KEY"),
    )
    setup_collection(qc)

    # Ingest all parsed markdown files in /data/parsed_docs/
    md_files = list(PARSED_DIR.glob("*.md"))
    if not md_files:
        print("No .md files found in data/parsed_docs/")
        print("Run scripts/parse_pdfs.py first, OR place MPEP markdown files manually.")
        print("\nExpected files like:")
        print("  data/parsed_docs/mpep_2100.md  (source='MPEP', section='2100')")
        print("  data/parsed_docs/35usc.md      (source='35 USC', section='full')")
        return

    total = 0
    for md_path in md_files:
        # Derive source/section from filename convention: source_section.md
        name = md_path.stem  # e.g. "mpep_2100"
        parts = name.split("_", 1)
        source = parts[0].upper().replace("USC", "35 USC").replace("CFR", "37 CFR")
        section = parts[1] if len(parts) > 1 else "full"
        total += ingest_markdown_file(md_path, source, section, vc, qc)

    print(f"\nIngested {total} chunks into Qdrant collection '{COLLECTION}'.")


if __name__ == "__main__":
    main()
