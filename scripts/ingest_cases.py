"""
Ingest patent litigation cases from Midpage into /data/raw/cases/ and
/data/cases_metadata.csv.

Usage:
  python scripts/ingest_cases.py            # full run
  python scripts/ingest_cases.py --seed     # seed 30 landmark cases only (fast path)
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.midpage_client import MidpageClient

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw" / "cases"
METADATA_CSV = DATA_DIR / "cases_metadata.csv"

# ── Seed cases: 30 landmark CAFC cases guaranteed to produce a rich demo graph ──
SEED_CITATIONS = [
    "573 U.S. 208",          # Alice Corp v. CLS Bank Int'l (2014)
    "792 F.3d 1339",         # Williamson v. Citrix Online (2015)
    "822 F.3d 1327",         # Enfish v. Microsoft (2016)
    "837 F.3d 1299",         # McRO v. Bandai Namco (2016)
    "881 F.3d 1360",         # Berkheimer v. HP Inc. (2018)
    "882 F.3d 1121",         # Aatrix Software v. Green Shades (2018)
    "850 F.3d 1343",         # Thales Visionix v. United States (2017)
    "927 F.3d 1306",         # Cellspin Soft v. Fitbit (2019)
    "967 F.3d 1285",         # American Axle v. Neapco Holdings (2019)
    "955 F.3d 1317",         # Ericsson v. TCL Communication (2018)
    "879 F.3d 1299",         # Finjan v. Blue Coat Systems (2018)
    "880 F.3d 1356",         # Core Wireless v. LG Electronics (2018)
    "908 F.3d 1343",         # Ancora Technologies v. HTC America (2018)
    "930 F.3d 1295",         # SRI International v. Cisco Systems (2019)
    "921 F.3d 1084",         # Trading Technologies v. IBG (2019)
    "550 U.S. 398",          # KSR International v. Teleflex (2007)
    "383 U.S. 1",            # Graham v. John Deere (1966)
    "415 F.3d 1303",         # Phillips v. AWH Corp (2005)
    "517 U.S. 370",          # Markman v. Westview Instruments (1996)
    "566 U.S. 66",           # Mayo Collaborative v. Prometheus (2012)
    "569 U.S. 576",          # Myriad Genetics (2013)
    "773 F.3d 1245",         # DDR Holdings v. Hotels.com (2014)
    "772 F.3d 709",          # Ultramercial v. Hulu (2014)
    "827 F.3d 1341",         # Bascom Global v. AT&T Mobility (2016)
    "830 F.3d 1350",         # Electric Power Group v. Alstom (2016)
    "823 F.3d 607",          # TLI Communications v. AV Automotive (2016)
    "841 F.3d 1288",         # Amdocs v. Openet Telecom (2016)
    "867 F.3d 1253",         # Visual Memory v. NVIDIA (2017)
    "887 F.3d 1376",         # Voter Verified v. Election Systems (2018)
]

SEARCH_QUERIES = {
    "eligibility_alice": "Alice Corp patent eligibility software abstract idea",
    "eligibility_mayo": "35 USC 101 two-step Mayo framework Federal Circuit",
    "claim_construction": "claim construction Markman Federal Circuit means plus function",
    "indefiniteness": "Williamson 112f indefiniteness written description",
    "obviousness_ksr": "KSR obviousness motivation to combine prior art",
    "secondary_considerations": "Graham v John Deere secondary considerations nonobviousness",
    "ptab_1": "inter partes review final written decision unpatentable",
    "ptab_2": "IPR obviousness claim unpatentability software",
    "ptab_markman": "claim construction order Markman hearing NDCA patent",
}


CSV_FIELDS = ["case_id", "citation_str", "court", "date_decided", "judge", "full_text_path"]


def _load_existing_ids() -> set[str]:
    if not METADATA_CSV.exists():
        return set()
    with open(METADATA_CSV) as f:
        reader = csv.DictReader(f)
        return {row["case_id"] for row in reader}


def _append_rows(rows: list[dict]):
    write_header = not METADATA_CSV.exists()
    with open(METADATA_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def _extract_row(case: dict) -> dict:
    """Normalize a raw Midpage case dict into our CSV schema."""
    case_id = case.get("id") or case.get("case_id") or ""
    full_text_path = str(RAW_DIR / f"{case_id}.json") if case_id else ""
    return {
        "case_id": case_id,
        "citation_str": case.get("citation") or case.get("citation_str") or "",
        "court": case.get("court") or case.get("jurisdiction") or "",
        "date_decided": case.get("date_decided") or case.get("date") or "",
        "judge": case.get("judge") or case.get("judges") or "",
        "full_text_path": full_text_path,
    }


def ingest_seed(client: MidpageClient, existing: set[str]) -> list[str]:
    """Ingest the 30 landmark seed cases by citation string."""
    new_ids = []
    for citation in SEED_CITATIONS:
        print(f"  Seed: {citation}")
        case = client.search_by_citation(citation)
        if not case:
            print(f"    WARNING: not found in Midpage — skipping")
            continue
        case_id = case.get("id") or case.get("case_id")
        if not case_id or case_id in existing:
            continue
        try:
            full_case = client.get_case(case_id)
        except Exception as e:
            print(f"    WARNING: could not fetch full text for {case_id}: {e}")
            full_case = case
        row = _extract_row(full_case)
        _append_rows([row])
        existing.add(case_id)
        new_ids.append(case_id)
        time.sleep(0.3)
    return new_ids


def ingest_search_queries(client: MidpageClient, existing: set[str]) -> list[str]:
    """Run all search queries and ingest results."""
    new_ids = []
    for label, query in SEARCH_QUERIES.items():
        print(f"\n  Query [{label}]: {query[:60]}…")
        try:
            results = client.search(query, jurisdiction="cafc", limit=50)
        except Exception as e:
            print(f"    WARNING: search failed: {e}")
            continue
        print(f"    Got {len(results)} results")
        batch = []
        for r in results:
            case_id = r.get("id") or r.get("case_id")
            if not case_id or case_id in existing:
                continue
            try:
                full_case = client.get_case(case_id)
            except Exception as e:
                print(f"    WARNING: case fetch failed {case_id}: {e}")
                full_case = r
            batch.append(_extract_row(full_case))
            existing.add(case_id)
            new_ids.append(case_id)
            time.sleep(0.2)
        if batch:
            _append_rows(batch)
            print(f"    Added {len(batch)} new cases")

    # Also pull PTAB and NDCA Markman results
    extra_queries = [
        ("inter partes review final written decision unpatentable 101 software", "all"),
        ("claim construction order Markman hearing NDCA patent", "ndca"),
    ]
    for query, jurisdiction in extra_queries:
        print(f"\n  Extra query [{jurisdiction}]: {query[:60]}…")
        try:
            results = client.search(query, jurisdiction=jurisdiction, limit=15)
        except Exception as e:
            print(f"    WARNING: search failed: {e}")
            continue
        batch = []
        for r in results:
            case_id = r.get("id") or r.get("case_id")
            if not case_id or case_id in existing:
                continue
            try:
                full_case = client.get_case(case_id)
            except Exception as e:
                full_case = r
            batch.append(_extract_row(full_case))
            existing.add(case_id)
            new_ids.append(case_id)
            time.sleep(0.2)
        if batch:
            _append_rows(batch)

    return new_ids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", action="store_true", help="Ingest seed cases only")
    args = parser.parse_args()

    client = MidpageClient()
    existing = _load_existing_ids()
    print(f"Starting with {len(existing)} existing cases.")

    print("\n=== Ingesting seed cases ===")
    seed_ids = ingest_seed(client, existing)
    print(f"Added {len(seed_ids)} seed cases.")

    if not args.seed:
        print("\n=== Running search queries ===")
        query_ids = ingest_search_queries(client, existing)
        print(f"Added {len(query_ids)} cases from search queries.")

    total = len(_load_existing_ids())
    print(f"\nDone. Total cases in corpus: {total}")
    print(f"Metadata CSV: {METADATA_CSV}")


if __name__ == "__main__":
    main()
