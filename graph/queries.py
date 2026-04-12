"""
Neo4j query functions.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

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


# ── Graph query functions ─────────────────────────────────────────────────────

def get_precedent_chain(case_id: str, depth: int = 3) -> dict:
    """Traverse CITES edges up to `depth` hops from anchor case."""
    cypher = f"""
    MATCH path = (c:Case {{id: $case_id}})-[:CITES*1..{depth}]->(ancestor:Case)
    RETURN ancestor.id       AS id,
           ancestor.citation AS citation,
           ancestor.holding_summary AS holding_summary,
           ancestor.date_filed      AS date_filed,
           ancestor.court           AS court,
           length(path)             AS hops
    ORDER BY hops ASC, ancestor.date_filed DESC
    LIMIT 25
    """
    rows = _run(cypher, {"case_id": case_id})

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

    node_ids = [n["id"] for n in nodes]
    edge_rows = _run(
        "MATCH (a:Case)-[r:CITES]->(b:Case) WHERE a.id IN $ids AND b.id IN $ids "
        "RETURN a.id AS source, b.id AS target, type(r) AS type",
        {"ids": node_ids},
    )
    edges = [{"source": e["source"], "target": e["target"], "type": e["type"]} for e in edge_rows]

    return {"nodes": nodes, "edges": edges}


def find_cases_by_citation(citation_str: str) -> list[dict]:
    """Search Neo4j for cases whose citation contains the given string."""
    rows = _run(
        "MATCH (c:Case) WHERE toLower(c.citation) CONTAINS toLower($q) "
        "RETURN c.id AS id, c.citation AS citation, c.court AS court, "
        "c.date_filed AS date, c.holding_summary AS holding_summary LIMIT 5",
        {"q": citation_str},
    )
    return [dict(r) for r in rows]


def get_claim_construction_cluster(patent_number: str) -> dict:
    cypher = """
    MATCH (p:Patent {number: $patent_number})-[:HAS_CLAIM]->(cl:Claim)-[:CONSTRUED_IN]->(c:Case)
    RETURN c.id AS case_id, c.citation AS citation,
           cl.scope_ruling AS scope_ruling, cl.text_excerpt AS excerpt
    LIMIT 25
    """
    rows = _run(cypher, {"patent_number": patent_number})
    return {"patent": patent_number, "constructions": rows}


def detect_circuit_split(case_ids: list[str]) -> dict:
    cypher = """
    MATCH (c:Case)-[:HEARD_BY]->(ct:Court)
    WHERE c.id IN $case_ids
    RETURN c.id AS case_id, c.citation AS citation,
           c.holding_summary AS holding_summary,
           ct.name AS court, c.date_filed AS date
    ORDER BY ct.name, c.date_filed DESC
    """
    rows = _run(cypher, {"case_ids": case_ids})
    courts: dict[str, list] = {}
    for r in rows:
        courts.setdefault(r["court"], []).append(r)
    return {"exists": len(courts) > 1, "courts": courts, "cases": rows}


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
    nodes = [dict(r) for r in nodes_rows]
    edges = [dict(r) for r in cite_edges]
    return {"nodes": nodes, "edges": edges}
