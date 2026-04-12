"""
Retrieve statutory grounding from Qdrant for a given query.
"""

import os

import voyageai
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

COLLECTION = "patent_statutes"
VOYAGE_MODEL = "voyage-law-2"

_vc = None
_qc = None


def _clients():
    global _vc, _qc
    if _vc is None:
        _vc = voyageai.Client(api_key=os.environ["VOYAGE_API_KEY"])
    if _qc is None:
        _qc = QdrantClient(
            url=os.environ["QDRANT_URL"],
            api_key=os.environ.get("QDRANT_API_KEY"),
        )
    return _vc, _qc


def retrieve_statutory_grounding(query_text: str, top_k: int = 4) -> list[dict]:
    """
    Embed query with voyage-law-2, search Qdrant, return top_k chunks.
    Returns list of dicts: {source, section, text, score}
    """
    vc, qc = _clients()

    try:
        result = vc.embed([query_text], model=VOYAGE_MODEL, input_type="query")
        query_emb = result.embeddings[0]
    except Exception as e:
        print(f"  WARNING: Voyage embedding failed: {e}")
        return []

    try:
        hits = qc.search(
            collection_name=COLLECTION,
            query_vector=query_emb,
            limit=top_k,
        )
    except Exception as e:
        print(f"  WARNING: Qdrant search failed: {e}")
        return []

    return [
        {
            "source": h.payload.get("source", ""),
            "section": h.payload.get("section", ""),
            "text": h.payload.get("text", ""),
            "score": h.score,
        }
        for h in hits
    ]
