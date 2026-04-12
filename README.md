# PatentGraph — Patent Litigation Intelligence

Stanford LLM × Law Hackathon #6 · Harvey Challenge

## Quick Start

```bash
# 1. Python env
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Env vars — copy and fill in your keys
cp .env.example .env

# 3. Test Midpage API first
python scripts/midpage_client.py

# 4. Ingest seed cases (30 landmark CAFC cases)
python scripts/ingest_cases.py --seed

# 5. Embed + build edges
python scripts/embed_cases.py
python scripts/build_citation_edges.py
python scripts/build_semantic_edges.py
python scripts/extract_claims.py

# 6. Load Neo4j
python scripts/neo4j_setup.py
python scripts/load_cases.py
python scripts/load_claims.py
python scripts/load_citation_edges.py
python scripts/load_semantic_edges.py

# 7. (Optional) Parse MPEP PDFs + load Qdrant
python scripts/parse_pdfs.py        # place PDFs in data/raw/pdfs/
python rag/ingest_corpus.py

# 8. Cache demo responses
python demo/cache_responses.py

# 9. Start API
uvicorn api.main:app --reload

# 10. Start frontend (separate terminal)
cd frontend && npm install && npm run dev
```

## Execution Order (fast path for demo)

| Step | Script | Notes |
|------|--------|-------|
| 1 | `scripts/midpage_client.py` | Smoke test — fix BASE_URL/auth first |
| 2 | `scripts/ingest_cases.py --seed` | 30 landmark cases |
| 3 | `scripts/embed_cases.py` | voyage-law-2 |
| 4 | `scripts/build_citation_edges.py` | |
| 5 | `scripts/build_semantic_edges.py` | |
| 6 | `scripts/extract_claims.py` | |
| 7 | `scripts/neo4j_setup.py` | Run once |
| 8 | `scripts/load_cases.py` | |
| 9 | `scripts/load_claims.py` | |
| 10 | `scripts/load_citation_edges.py` | |
| 11 | `scripts/load_semantic_edges.py` | |
| 12 | `rag/ingest_corpus.py` | After parse_pdfs.py |
| 13 | `uvicorn api.main:app --reload` | Backend |
| 14 | `cd frontend && npm run dev` | Frontend |

## IMPORTANT: Midpage API Setup

Before running anything, update `scripts/midpage_client.py`:

```python
BASE_URL = "https://api.midpage.ai/v1"    # confirm from docs
AUTH_HEADER_NAME = "X-Api-Key"             # confirm from docs
```

Read the API docs at https://bit.ly/4caSNXS for the exact endpoint paths,
auth header, and response schema. The client is designed to be easy to adapt.

## Architecture

```
Attorney Question
    │
    ▼
voyage-law-2 embedding
    │
    ├─► Neo4j: vector search → precedent chain traversal
    │
    ├─► Midpage API: live case law retrieval
    │
    └─► Qdrant: MPEP + 35 USC + 37 CFR statutory retrieval
              │
              ▼
           Claude (claude-sonnet-4-20250514)
              │
              ▼
         TrustFoundry citation verification
              │
              ▼
       Structured legal memo JSON
              │
              ▼
   Cytoscape.js graph + memo panel
```

## Demo Queries (use with demo=true for cached responses)

1. **Eligibility**: "How has the Federal Circuit treated software patent eligibility under Alice after 2019? Which judges apply the two-step test most strictly?"

2. **Claim Construction**: "What is the CAFC standard for means-plus-function construction under 35 USC 112(f)? How has it shifted since Williamson v. Citrix?"

3. **Obviousness**: "After KSR, how do NDCA district courts handle obviousness challenges to software patents with UI claim elements?"
