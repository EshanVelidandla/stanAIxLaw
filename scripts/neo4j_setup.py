"""
Create Neo4j constraints and indexes.

Usage: python scripts/neo4j_setup.py
"""

import os
import sys
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

SETUP_QUERIES = [
    "CREATE CONSTRAINT case_id IF NOT EXISTS FOR (c:Case) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT patent_id IF NOT EXISTS FOR (p:Patent) REQUIRE p.number IS UNIQUE",
    "CREATE CONSTRAINT court_id IF NOT EXISTS FOR (ct:Court) REQUIRE ct.name IS UNIQUE",
    "CREATE CONSTRAINT judge_id IF NOT EXISTS FOR (j:Judge) REQUIRE j.name IS UNIQUE",
    "CREATE INDEX case_date IF NOT EXISTS FOR (c:Case) ON (c.date_filed)",
    "CREATE INDEX case_court IF NOT EXISTS FOR (c:Case) ON (c.court)",
]


def main():
    uri = os.environ["NEO4J_URI"]
    user = os.environ["NEO4J_USERNAME"]
    pwd = os.environ["NEO4J_PASSWORD"]

    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    with driver.session() as session:
        for q in SETUP_QUERIES:
            print(f"  {q[:60]}…")
            session.run(q)
    driver.close()
    print("Neo4j setup complete.")


if __name__ == "__main__":
    main()
