"""
Patent query orchestration: embed -> graph search -> Midpage -> Claude.
"""

import json
import os
import sys

import anthropic
import voyageai
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from graph.queries import get_precedent_chain, vector_search_cases
from llm.prompts import SYSTEM_PROMPT
from rag.retrieval import retrieve_statutory_grounding
from scripts.midpage_client import MidpageClient

VOYAGE_MODEL = "voyage-law-2"
CLAUDE_MODEL = "claude-sonnet-4-20250514"

_vc = None
_midpage = None


def _voyage():
    global _vc
    if _vc is None:
        _vc = voyageai.Client(api_key=os.environ["VOYAGE_API_KEY"])
    return _vc


def _midpage_client():
    global _midpage
    if _midpage is None:
        _midpage = MidpageClient()
    return _midpage


def run_patent_query(attorney_question: str) -> dict:
    print(f"\n[query] '{attorney_question[:80]}…'")

    # Step 1: Embed question
    print("  [1/5] Embedding query…")
    try:
        result = _voyage().embed([attorney_question], model=VOYAGE_MODEL, input_type="query")
        query_embedding = result.embeddings[0]
    except Exception as e:
        print(f"  WARNING: embedding failed: {e}")
        query_embedding = None

    # Step 2: Vector search for anchor cases
    anchor_cases = []
    if query_embedding:
        print("  [2/5] Finding anchor cases…")
        anchor_cases = vector_search_cases(query_embedding, top_k=5)
        print(f"    Anchors: {[c['citation'] for c in anchor_cases]}")

    # Step 3: Expand to subgraph via Neo4j
    print("  [3/5] Expanding precedent chain…")
    subgraph_nodes, subgraph_edges = [], []
    seen: set[str] = set()
    for case in anchor_cases:
        try:
            chain = get_precedent_chain(case["id"], depth=2)
            for n in chain["nodes"]:
                if n["id"] not in seen:
                    seen.add(n["id"])
                    n["is_anchor"] = (n["id"] == case["id"])
                    subgraph_nodes.append(n)
            subgraph_edges.extend(chain["edges"])
        except Exception as e:
            print(f"    WARNING: graph query failed for {case['id']}: {e}")

    unique_nodes = subgraph_nodes[:20]
    unique_edges = list({(e["source"], e["target"]): e for e in subgraph_edges}.values())
    subgraph_json = {"nodes": unique_nodes, "edges": unique_edges}
    print(f"    Subgraph: {len(unique_nodes)} nodes, {len(unique_edges)} edges")

    # Step 4a: Midpage live retrieval
    print("  [4a/5] Midpage live retrieval…")
    midpage_text = ""
    try:
        results = _midpage_client().search(attorney_question, jurisdiction="cafc", limit=6)
        midpage_text = "\n\n".join([
            f"[Midpage | {r.get('citation','?')} | {r.get('date','')}]: "
            f"{r.get('snippet') or r.get('full_text','')[:400]}"
            for r in results
        ])
        print(f"    Midpage: {len(results)} results")
    except Exception as e:
        print(f"    WARNING: Midpage search failed: {e}")
        midpage_text = "[Midpage retrieval unavailable]"

    # Step 4b: Statutory grounding
    print("  [4b/5] Qdrant statutory retrieval…")
    statutory_text = ""
    try:
        statutory = retrieve_statutory_grounding(attorney_question, top_k=4)
        statutory_text = "\n\n".join([
            f"[{p['source']} {p['section']}]: {p['text']}"
            for p in statutory
        ])
        print(f"    Statutory: {len(statutory)} chunks")
    except Exception as e:
        print(f"    WARNING: Qdrant retrieval failed: {e}")
        statutory_text = "[Statutory retrieval unavailable]"

    # Step 5: Claude call
    print("  [5/5] Calling Claude…")
    user_message = f"""ATTORNEY QUESTION: {attorney_question}

SUBGRAPH ({len(unique_nodes)} cases from knowledge graph):
{json.dumps(subgraph_json, indent=2)}

LIVE CASE LAW (Midpage, real-time retrieval):
{midpage_text}

STATUTORY GROUNDING (MPEP, 35 USC, 37 CFR):
{statutory_text}

Produce the structured legal memo JSON."""

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3].strip()

    memo = json.loads(raw)
    memo["subgraph"] = subgraph_json
    memo["anchor_cases"] = [c["id"] for c in anchor_cases]
    print("  Done.")
    return memo
