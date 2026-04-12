"""
Neo4j query functions and in-memory vector search.

Loaded at startup — embeddings matrix kept in memory for fast cosine search.
"""

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
from dotenv import load_dotenv
from neo4j import GraphDatabase
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
EMB_DIR = DATA_DIR / "embeddings"
EMB_INDEX = DATA_DIR / "embeddings_index.json"
METADATA_CSV = DATA_DIR / "cases_metadata.csv"

# ── Neo4j driver (lazy singleton) ─────────────────────────────────────────────

_driver = None


def _get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            os.environ["NEO4J_URI"],
            auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
        )
    return _driver


def _run(cypher: str, params: dict = {}) -> list[dict]:
    driver = _get_driver()
    with driver.session() as session:
        result = session.run(cypher, params)
        return [dict(r) for r in result]


# ── In-memory embedding cache (loaded once at import time) ───────────────────

_emb_matrix: np.ndarray | None = None
_emb_ids: list[str] = []
_case_metadata: dict[str, dict] = {}


def _load_embeddings():
    global _emb_matrix, _emb_ids, _case_metadata
    if _emb_matrix is not None:
        return

    import csv
    with open(METADATA_CSV) as f:
        for row in csv.DictReader(f):
            _case_metadata[row["case_id"]] = row

    if not EMB_INDEX.exists():
        _emb_matrix = np.zeros((0, 1024), dtype=np.float32)
        return

    index: dict[str, str] = json.loads(EMB_INDEX.read_text())
    rows, ids = [], []
    for cid, path in index.items():
        p = Path(path)
        if p.exists():
            rows.append(np.load(str(p)))
            ids.append(cid)

    _emb_ids = ids
    _emb_matrix = np.vstack(rows) if rows else np.zeros((0, 1024), dtype=np.float32)


def vector_search_cases(query_embedding: list[float], top_k: int = 5) -> list[dict]:
    """Cosine similarity search over in-memory embedding matrix."""
    _load_embeddings()
    if _emb_matrix.shape[0] == 0:
        return []
    q = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
    sims = cosine_similarity(q, _emb_matrix)[0]
    top_idx = np.argsort(sims)[::-1][:top_k]
    results = []
    for idx in top_idx:
        cid = _emb_ids[idx]
        meta = _case_metadata.get(cid, {"case_id": cid})
        results.append({
            "id": cid,
            "citation": meta.get("citation_str", ""),
            "court": meta.get("court", ""),
            "date": meta.get("date_decided", ""),
            "score": float(sims[idx]),
        })
    return results


# ── Graph query functions ─────────────────────────────────────────────────────

def get_precedent_chain(case_id: str, depth: int = 3) -> dict:
    """Traverse CITES edges up to `depth` hops from anchor case."""
    cypher = """
    MATCH path = (c:Case {id: $case_id})-[:CITES*1..$depth]->(ancestor:Case)
    RETURN ancestor.id       AS id,
           ancestor.citation AS citation,
           ancestor.holding_summary AS holding_summary,
           ancestor.date_filed      AS date_filed,
           ancestor.court           AS court,
           length(path)             AS hops
    ORDER BY hops ASC, ancestor.date_filed DESC
    LIMIT 25
    """
    rows = _run(cypher, {"case_id": case_id, "depth": depth})

    # Also pull anchor node itself
    anchor_rows = _run(
        "MATCH (c:Case {id: $id}) RETURN c.id AS id, c.citation AS citation, "
        "c.holding_summary AS holding_summary, c.date_filed AS date_filed, c.court AS court",
        {"id": case_id},
    )
    anchor = anchor_rows[0] if anchor_rows else {"id": case_id, "citation": "", "hops": 0}

    nodes = [{"id": r["id"], "citation": r["citation"], "holding_summary": r["holding_summary"],
               "date": r["date_filed"], "court": r["court"], "hops": r["hops"]}
             for r in rows]
    nodes.insert(0, {**anchor, "hops": 0})

    # Pull edges between these node IDs
    node_ids = [n["id"] for n in nodes]
    edge_rows = _run(
        "MATCH (a:Case)-[r:CITES]->(b:Case) WHERE a.id IN $ids AND b.id IN $ids "
        "RETURN a.id AS source, b.id AS target, type(r) AS type",
        {"ids": node_ids},
    )
    edges = [{"source": e["source"], "target": e["target"], "type": e["type"]} for e in edge_rows]

    return {"nodes": nodes, "edges": edges}


def get_claim_construction_cluster(patent_number: str) -> dict:
    cypher = """
    MATCH (p:Patent {number: $patent_number})-[:HAS_CLAIM]->(cl:Claim)-[:CONSTRUED_IN]->(c:Case)
    OPTIONAL MATCH (c)-[:SIMILAR_TO]-(similar:Case)
    RETURN c.id AS case_id, c.citation AS citation,
           cl.scope_ruling AS scope_ruling, cl.text_excerpt AS excerpt,
           collect(similar.citation)[0..3] AS related_citations
    LIMIT 25
    """
    rows = _run(cypher, {"patent_number": patent_number})
    return {"patent": patent_number, "constructions": rows}


def detect_circuit_split(similar_case_ids: list[str]) -> dict:
    cypher = """
    MATCH (c:Case)-[:HEARD_BY]->(ct:Court)
    WHERE c.id IN $similar_case_ids
    RETURN c.id AS case_id, c.citation AS citation,
           c.holding_summary AS holding_summary,
           ct.name AS court, c.date_filed AS date
    ORDER BY ct.name, c.date_filed DESC
    """
    rows = _run(cypher, {"similar_case_ids": similar_case_ids})

    # Detect split: multiple courts with different holdings on same issue
    courts: dict[str, list] = {}
    for r in rows:
        courts.setdefault(r["court"], []).append(r)

    split_exists = len(courts) > 1
    return {
        "exists": split_exists,
        "courts": courts,
        "cases": rows,
    }


def get_judge_pattern(judge_name: str) -> dict:
    cypher = """
    MATCH (j:Judge {name: $judge_name})<-[:DECIDED_BY]-(c:Case)
    OPTIONAL MATCH (c)<-[:CONSTRUED_IN]-(cl:Claim)
    RETURN c.id AS case_id, c.citation AS citation, c.date_filed AS date,
           cl.scope_ruling AS scope_ruling, c.holding_summary AS summary
    ORDER BY c.date_filed DESC
    LIMIT 30
    """
    rows = _run(cypher, {"judge_name": judge_name})

    scope_counts: dict[str, int] = {}
    for r in rows:
        s = r.get("scope_ruling") or "unknown"
        scope_counts[s] = scope_counts.get(s, 0) + 1

    return {"judge": judge_name, "cases": rows, "scope_pattern": scope_counts}


def get_full_subgraph(node_ids: list[str]) -> dict:
    """Return nodes + all edge types between a set of case IDs."""
    nodes_rows = _run(
        "MATCH (c:Case) WHERE c.id IN $ids "
        "RETURN c.id AS id, c.citation AS citation, c.holding_summary AS holding_summary, "
        "c.date_filed AS date, c.court AS court",
        {"ids": node_ids},
    )
    cite_edges = _run(
        "MATCH (a:Case)-[:CITES]->(b:Case) WHERE a.id IN $ids AND b.id IN $ids "
        "RETURN a.id AS source, b.id AS target, 'CITES' AS type",
        {"ids": node_ids},
    )
    sim_edges = _run(
        "MATCH (a:Case)-[r:SIMILAR_TO]-(b:Case) WHERE a.id IN $ids AND b.id IN $ids AND a.id < b.id "
        "RETURN a.id AS source, b.id AS target, 'SIMILAR_TO' AS type, r.weight AS weight",
        {"ids": node_ids},
    )
    nodes = [dict(r) for r in nodes_rows]
    edges = [dict(r) for r in cite_edges] + [dict(r) for r in sim_edges]
    return {"nodes": nodes, "edges": edges}
