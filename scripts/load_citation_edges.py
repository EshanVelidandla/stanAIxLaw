"""
Load CITES edges into Neo4j.

Usage: python scripts/load_citation_edges.py
"""

import csv
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
EDGES_CSV = DATA_DIR / "edges" / "citation_edges.csv"

MERGE_EDGE = """
MATCH (a:Case {id: $source_id}), (b:Case {id: $target_id})
MERGE (a)-[:CITES]->(b)
"""


def main():
    uri = os.environ["NEO4J_URI"]
    user = os.environ["NEO4J_USERNAME"]
    pwd = os.environ["NEO4J_PASSWORD"]
    driver = GraphDatabase.driver(uri, auth=(user, pwd))

    with open(EDGES_CSV) as f:
        rows = list(csv.DictReader(f))

    print(f"Loading {len(rows)} citation edges…")
    with driver.session() as session:
        for i, row in enumerate(rows):
            session.run(MERGE_EDGE, {"source_id": row["source_id"], "target_id": row["target_id"]})
            if (i + 1) % 200 == 0:
                print(f"  {i + 1}/{len(rows)}")

    driver.close()
    print("Citation edges loaded.")


if __name__ == "__main__":
    main()
