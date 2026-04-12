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
    # § 101 Software Eligibility
    "573 U.S. 208",          # Alice Corp v. CLS Bank Int'l (2014)
    "822 F.3d 1327",         # Enfish v. Microsoft (2016)
    "837 F.3d 1299",         # McRO v. Bandai Namco (2016)
    "881 F.3d 1360",         # Berkheimer v. HP Inc. (2018)
    "882 F.3d 1121",         # Aatrix Software v. Green Shades (2018)
    "850 F.3d 1343",         # Thales Visionix v. United States (2017)
    "927 F.3d 1306",         # Cellspin Soft v. Fitbit (2019)
    "967 F.3d 1285",         # American Axle v. Neapco Holdings (2019)
    "879 F.3d 1299",         # Finjan v. Blue Coat Systems (2018)
    "880 F.3d 1356",         # Core Wireless v. LG Electronics (2018)
    "908 F.3d 1343",         # Ancora Technologies v. HTC America (2018)
    "930 F.3d 1295",         # SRI International v. Cisco Systems (2019)
    "921 F.3d 1084",         # Trading Technologies v. IBG (2019)
    "773 F.3d 1245",         # DDR Holdings v. Hotels.com (2014)
    "772 F.3d 709",          # Ultramercial v. Hulu (2014)
    "827 F.3d 1341",         # Bascom Global v. AT&T Mobility (2016)
    "830 F.3d 1350",         # Electric Power Group v. Alstom (2016)
    "823 F.3d 607",          # TLI Communications v. AV Automotive (2016)
    "841 F.3d 1288",         # Amdocs v. Openet Telecom (2016)
    "867 F.3d 1253",         # Visual Memory v. NVIDIA (2017)
    "887 F.3d 1376",         # Voter Verified v. Election Systems (2018)
    "958 F.3d 1327",         # Uniloc USA v. LG Electronics (2020)
    "976 F.3d 1327",         # Cooperative Entertainment v. Kollective Technology (2020)
    "4 F.4th 1342",          # Weisner v. Google (2021)
    "55 F.4th 891",          # Cooperative Entertainment v. Kollective Technology (2022)

    # § 101 Biotech / Natural Phenomena
    "566 U.S. 66",           # Mayo Collaborative v. Prometheus (2012)
    "569 U.S. 576",          # Myriad Genetics (2013)
    "890 F.3d 1354",         # Vanda Pharmaceuticals v. West-Ward (2018)
    "903 F.3d 1286",         # Natural Alternatives v. Creative Compounds (2019)
    "976 F.3d 1358",         # American Axle v. Neapco (en banc cert denied) (2020)

    # Claim Construction
    "415 F.3d 1303",         # Phillips v. AWH Corp (2005)
    "517 U.S. 370",          # Markman v. Westview Instruments (1996)
    "792 F.3d 1339",         # Williamson v. Citrix Online (means-plus-function) (2015)
    "955 F.3d 1317",         # Ericsson v. TCL Communication (2018)
    "996 F.3d 1316",         # Sisvel International v. Sierra Wireless (2021)
    "965 F.3d 1372",         # Nevro Corp v. Boston Scientific (2020)
    "890 F.3d 1354",         # Vanda Pharmaceuticals v. West-Ward (2018)
    "946 F.3d 1310",         # Immunomedics v. Sandoz (2020)

    # Obviousness
    "550 U.S. 398",          # KSR International v. Teleflex (2007)
    "383 U.S. 1",            # Graham v. John Deere (1966)
    "800 F.3d 1340",         # Merck & Cie v. Gnosis (2015)
    "858 F.3d 1371",         # Arendi v. Apple (2017)
    "882 F.3d 1326",         # Personal Web Technologies v. Apple (2018)
    "996 F.3d 1350",         # Metalcraft of Mayville v. The Toro Company (2021)
    "951 F.3d 1359",         # Intercontinental Great Brands v. Kellogg North America (2020)

    # Damages
    "594 F.3d 860",          # Lucent Technologies v. Gateway (2009) — entire market value rule
    "767 F.3d 1338",         # VirnetX v. Cisco Systems (2014) — apportionment
    "840 F.3d 1044",         # Mentor Graphics v. EVE-USA (2016) — lost profits
    "869 F.3d 1349",         # Power Integrations v. Fairchild Semiconductor (2017)
    "946 F.3d 1290",         # Panduit Corp v. Stahlin Bros (2020)
    "971 F.3d 1359",         # Finjan v. SonicWall (2020) — royalty base
    "14 F.4th 1313",         # Ironburg Inventions v. Valve Corp (2021)
    "29 F.4th 1346",         # EcoServices v. Certified Aviation Services (2022)

    # Infringement / DOE
    "520 U.S. 17",           # Warner-Jenkinson v. Hilton Davis (doctrine of equivalents)
    "535 U.S. 722",          # Festo Corp v. Shoketsu Kinzoku (prosecution history estoppel)
    "815 F.3d 625",          # Verinata Health v. Ariosa Diagnostics (2016)
    "909 F.3d 1285",         # Nalco Company v. Chem-Mod (2018)
    "963 F.3d 1334",         # Nevro Corp v. Boston Scientific (2020)

    # PTAB / IPR / Post-Grant
    "584 U.S. 317",          # SAS Institute v. Iancu (2018) — IPR all claims
    "572 U.S. 898",          # Nautilus v. Biosig Instruments (2014) — definiteness
    "813 F.3d 1326",         # In re Cuozzo Speed Technologies (2016)
    "867 F.3d 1381",         # Aqua Products v. Matal (2017)
    "952 F.3d 1360",         # Arthrex v. Smith & Nephew (2020) — APJ appointments
    "141 S.Ct. 1970",        # United States v. Arthrex (2021)
    "979 F.3d 1363",         # Sand Revolution v. Continental Intermodal (2020)
    "898 F.3d 1177",         # In re Cellect (IPR estoppel) (2018)

    # Written Description / Enablement
    "598 F.3d 1336",         # Ariad Pharmaceuticals v. Eli Lilly (2010) — written description
    "976 F.3d 1347",         # Baxalta v. Genentech (2020) — functional claiming
    "10 F.4th 1328",         # Amgen v. Sanofi (2021) — enablement antibodies
    "987 F.3d 1375",         # Juno Therapeutics v. Kite Pharma (2021)

    # Injunctions & Enforcement
    "547 U.S. 388",          # eBay v. MercExchange (2006) — permanent injunction
    "769 F.3d 1371",         # Apple v. Samsung (2014) — causal nexus
    "839 F.3d 1034",         # Apple v. Samsung (2016) — design patent damages
    "926 F.3d 1362",         # Nichia Corp v. Everlight Americas (2019)

    # Enhanced Damages / Willfulness
    "579 U.S. 93",           # Halo Electronics v. Pulse Electronics (2016)
    "776 F.3d 837",          # Bard Peripheral Vascular v. W.L. Gore (2015)
    "890 F.3d 1272",         # WesternGeco v. ION Geophysical (2018) — extraterritorial damages

    # Patent Exhaustion
    "581 U.S. 360",          # Impression Products v. Lexmark International (2017)
    "553 U.S. 617",          # Quanta Computer v. LG Electronics (2008)

    # IPR Constitutionality & Procedure
    "584 U.S. 325",          # Oil States Energy Services v. Greene's Energy Group (2018)
    "590 U.S. 45",           # Thryv v. Click-to-Call Technologies (2020)
    "143 S.Ct. 898",         # Cuozzo Speed Technologies v. Lee (2016) SCOTUS

    # Claim Construction — Additional
    "574 U.S. 318",          # Teva Pharmaceuticals v. Sandoz (2015) — de novo review
    "521 F.3d 1351",         # O2 Micro International v. Beyond Innovation (2008)
    "800 F.3d 1366",         # Media Rights Technologies v. Capital One (2015)

    # § 101 — More Recent
    "874 F.3d 1329",         # Two-Way Media v. Comcast Cable (2017)
    "838 F.3d 1253",         # Affinity Labs v. DirecTV (2016)
    "898 F.3d 1161",         # SAP America v. InvestPic (2018)
    "920 F.3d 759",          # ChargePoint v. SemaConnect (2019)
    "934 F.3d 1373",         # MyMail v. ooVoo (2019)
    "935 F.3d 1341",         # Chamberlain Group v. Techtronic Industries (2019)
    "977 F.3d 1327",         # Interval Licensing v. AOL (2020)

    # Divided / Induced Infringement
    "797 F.3d 1020",         # Akamai Technologies v. Limelight Networks (2015)
    "572 U.S. 915",          # Limelight Networks v. Akamai Technologies (2014)

    # Inequitable Conduct
    "649 F.3d 1276",         # Therasense v. Becton Dickinson (2011) — materiality/intent

    # Written Description / Enablement — Additional
    "687 F.3d 1377",         # MagSil Corp v. Hitachi Global Storage (2012)
    "941 F.3d 1149",         # Idenix Pharmaceuticals v. Gilead Sciences (2019)
    "143 S.Ct. 1243",        # Amgen v. Sanofi (2023) SCOTUS — enablement
    "864 F.3d 1343",         # Regeneron Pharmaceuticals v. Merus (2017)

    # FRAND / Standard-Essential Patents
    "773 F.3d 1201",         # Ericsson v. D-Link Systems (2014) — FRAND royalty
    "809 F.3d 1295",         # CSIRO v. Cisco Systems (2015) — FRAND

    # Declaratory Judgment / Jurisdiction
    "549 U.S. 118",          # MedImmune v. Genentech (2007) — DJ standard
    "553 U.S. 678",          # Quanta Computer v. LG (exhaustion companion)

    # Design Patents
    "543 F.3d 665",          # Egyptian Goddess v. Swisa (2008) — design patent test
    "580 U.S. 593",          # Samsung Electronics v. Apple (2016) — design patent damages

    # Obviousness-Type Double Patenting
    "753 F.3d 1208",         # Gilead Sciences v. Natco Pharma (2014) — ODP

    # Prosecution Disclaimer
    "713 F.3d 1090",         # Biogen Idec v. GlaxoSmithKline (2013)

    # Recent CAFC 2021-2024
    "29 F.4th 1360",         # Novartis Pharmaceuticals v. HEC Pharm (2022)
    "56 F.4th 1361",         # Medtronic v. Teleflex (2023)
    "45 F.4th 1339",         # Kannuu v. Samsung Electronics (2022)
    "62 F.4th 1374",         # Telectronics v. Medtronic (2023)
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
    """Normalize a Midpage case dict into our CSV schema."""
    case_id = case.get("id") or ""
    full_text_path = str(RAW_DIR / f"{case_id}.json") if case_id else ""
    return {
        "case_id": case_id,
        "citation_str": case.get("citation_str") or case.get("citation") or "",
        "court": case.get("court") or "",
        "date_decided": case.get("date_decided") or "",
        "judge": case.get("judge") or "",
        "full_text_path": full_text_path,
    }


def ingest_seed(client: MidpageClient, existing: set[str]) -> list[str]:
    """Ingest all seed cases in batches of 50, then fetch full text."""
    unique_citations = list(dict.fromkeys(SEED_CITATIONS))  # dedupe, preserve order
    print(f"  Fetching {len(unique_citations)} unique seed citations in batches…")
    cases = []
    for i in range(0, len(unique_citations), 50):
        batch = unique_citations[i:i+50]
        result = client.get_by_citations(batch, include_content=True)
        cases.extend(result)
        print(f"    Batch {i//50 + 1}: got {len(result)} matches")
    print(f"  Total Midpage matches: {len(cases)}")

    new_ids = []
    batch = []
    for case in cases:
        case_id = case.get("id")
        if not case_id or case_id in existing:
            continue
        # Cache raw JSON
        cache_path = RAW_DIR / f"{case_id}.json"
        if not cache_path.exists():
            cache_path.write_text(json.dumps(case, indent=2))
        batch.append(_extract_row(case))
        existing.add(case_id)
        new_ids.append(case_id)

    if batch:
        _append_rows(batch)
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
        print("\n(Search endpoint not supported by Midpage API — seed-only mode)")
        query_ids = []

    total = len(_load_existing_ids())
    print(f"\nDone. Total cases in corpus: {total}")
    print(f"Metadata CSV: {METADATA_CSV}")


if __name__ == "__main__":
    main()
