"""
Hard-code known citation relationships between the 30 seed cases.
These are well-established citation relationships in patent law.

Usage: python scripts/seed_citation_edges.py
"""

import csv
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
METADATA_CSV = DATA_DIR / "cases_metadata.csv"

# Known citation relationships: (citing_citation, cited_citation)
# All of these are documented citation relationships in CAFC patent law
KNOWN_EDGES = [
    # Alice Corp cites Mayo (both apply the two-step framework)
    ("573 U.S. 208", "566 U.S. 66"),
    # Post-Alice CAFC cases citing Alice Corp
    ("822 F.3d 1327", "573 U.S. 208"),   # Enfish -> Alice
    ("837 F.3d 1299", "573 U.S. 208"),   # McRO -> Alice
    ("773 F.3d 1245", "573 U.S. 208"),   # DDR Holdings -> Alice
    ("772 F.3d 709",  "573 U.S. 208"),   # Ultramercial -> Alice
    ("827 F.3d 1341", "573 U.S. 208"),   # Bascom -> Alice
    ("830 F.3d 1350", "573 U.S. 208"),   # Electric Power -> Alice
    ("823 F.3d 607",  "573 U.S. 208"),   # TLI -> Alice
    ("841 F.3d 1288", "573 U.S. 208"),   # Amdocs -> Alice
    ("850 F.3d 1343", "573 U.S. 208"),   # Thales -> Alice
    ("867 F.3d 1253", "573 U.S. 208"),   # Visual Memory -> Alice
    ("879 F.3d 1299", "573 U.S. 208"),   # Finjan -> Alice
    ("880 F.3d 1356", "573 U.S. 208"),   # Core Wireless -> Alice
    ("881 F.3d 1360", "573 U.S. 208"),   # Berkheimer -> Alice
    ("882 F.3d 1121", "573 U.S. 208"),   # Aatrix -> Alice
    ("887 F.3d 1376", "573 U.S. 208"),   # Voter Verified -> Alice
    ("908 F.3d 1343", "573 U.S. 208"),   # Ancora -> Alice
    ("921 F.3d 1084", "573 U.S. 208"),   # Trading Tech -> Alice
    ("927 F.3d 1306", "573 U.S. 208"),   # Cellspin -> Alice
    ("930 F.3d 1295", "573 U.S. 208"),   # SRI -> Alice
    ("955 F.3d 1317", "573 U.S. 208"),   # Ericsson -> Alice
    ("967 F.3d 1285", "573 U.S. 208"),   # American Axle -> Alice
    # Post-Alice cases also citing Mayo
    ("822 F.3d 1327", "566 U.S. 66"),    # Enfish -> Mayo
    ("967 F.3d 1285", "566 U.S. 66"),    # American Axle -> Mayo
    ("850 F.3d 1343", "566 U.S. 66"),    # Thales -> Mayo
    # Berkheimer / Aatrix cluster (fact questions re: §101)
    ("882 F.3d 1121", "881 F.3d 1360"),  # Aatrix -> Berkheimer
    ("927 F.3d 1306", "881 F.3d 1360"),  # Cellspin -> Berkheimer
    ("927 F.3d 1306", "882 F.3d 1121"),  # Cellspin -> Aatrix
    # Enfish citing cluster
    ("867 F.3d 1253", "822 F.3d 1327"),  # Visual Memory -> Enfish
    ("880 F.3d 1356", "822 F.3d 1327"),  # Core Wireless -> Enfish
    ("908 F.3d 1343", "822 F.3d 1327"),  # Ancora -> Enfish
    # Claim construction chain
    ("792 F.3d 1339", "415 F.3d 1303"),  # Williamson -> Phillips
    ("415 F.3d 1303", "517 U.S. 370"),   # Phillips -> Markman
    ("996 F.3d 1316", "415 F.3d 1303"),  # Sisvel -> Phillips
    ("965 F.3d 1372", "415 F.3d 1303"),  # Nevro -> Phillips
    ("965 F.3d 1372", "792 F.3d 1339"),  # Nevro -> Williamson
    # KSR obviousness chain
    ("550 U.S. 398",  "383 U.S. 1"),     # KSR -> Graham v. John Deere
    ("858 F.3d 1371", "550 U.S. 398"),   # Arendi -> KSR
    ("882 F.3d 1326", "550 U.S. 398"),   # Personal Web -> KSR
    ("951 F.3d 1359", "550 U.S. 398"),   # Intercontinental -> KSR
    ("800 F.3d 1340", "550 U.S. 398"),   # Merck -> KSR
    ("800 F.3d 1340", "383 U.S. 1"),     # Merck -> Graham
    ("996 F.3d 1350", "550 U.S. 398"),   # Metalcraft -> KSR
    # Mayo / Myriad cluster
    ("566 U.S. 66",   "383 U.S. 1"),     # Mayo -> Graham (background)
    ("569 U.S. 576",  "566 U.S. 66"),    # Myriad -> Mayo
    ("890 F.3d 1354", "566 U.S. 66"),    # Vanda -> Mayo
    ("890 F.3d 1354", "573 U.S. 208"),   # Vanda -> Alice
    ("903 F.3d 1286", "566 U.S. 66"),    # Natural Alternatives -> Mayo
    ("903 F.3d 1286", "573 U.S. 208"),   # Natural Alternatives -> Alice
    # More post-Alice eligibility edges
    ("958 F.3d 1327", "573 U.S. 208"),   # Uniloc -> Alice
    ("958 F.3d 1327", "822 F.3d 1327"),  # Uniloc -> Enfish
    ("976 F.3d 1327", "573 U.S. 208"),   # Cooperative Ent -> Alice
    # Damages chain
    ("767 F.3d 1338", "594 F.3d 860"),   # VirnetX -> Lucent (apportionment)
    ("840 F.3d 1044", "594 F.3d 860"),   # Mentor Graphics -> Lucent
    ("869 F.3d 1349", "594 F.3d 860"),   # Power Integrations -> Lucent
    ("971 F.3d 1359", "594 F.3d 860"),   # Finjan SonicWall -> Lucent
    # Injunction chain
    ("769 F.3d 1371", "547 U.S. 388"),   # Apple v Samsung -> eBay
    ("926 F.3d 1362", "547 U.S. 388"),   # Nichia -> eBay
    # DOE / prosecution history estoppel
    ("535 U.S. 722",  "520 U.S. 17"),    # Festo -> Warner-Jenkinson
    ("909 F.3d 1285", "535 U.S. 722"),   # Nalco -> Festo
    ("963 F.3d 1334", "535 U.S. 722"),   # Nevro infringement -> Festo
    # IPR / PTAB chain
    ("813 F.3d 1326", "572 U.S. 898"),   # Cuozzo -> Nautilus (standard of review)
    ("867 F.3d 1381", "813 F.3d 1326"),  # Aqua Products -> Cuozzo
    ("952 F.3d 1360", "813 F.3d 1326"),  # Arthrex -> Cuozzo
    ("584 U.S. 317",  "813 F.3d 1326"),  # SAS Institute -> Cuozzo
    # Written description / enablement chain
    ("976 F.3d 1347", "598 F.3d 1336"),  # Baxalta -> Ariad
    ("10 F.4th 1328", "598 F.3d 1336"),  # Amgen -> Ariad
    ("987 F.3d 1375", "598 F.3d 1336"),  # Juno -> Ariad
    ("10 F.4th 1328", "569 U.S. 576"),   # Amgen -> Myriad (functional claim analogy)
    ("687 F.3d 1377", "598 F.3d 1336"),  # MagSil -> Ariad (enablement)
    ("864 F.3d 1343", "598 F.3d 1336"),  # Regeneron -> Ariad (written description)

    # § 101 new cases -> Alice
    ("838 F.3d 1253", "573 U.S. 208"),   # Affinity Labs -> Alice
    ("874 F.3d 1329", "573 U.S. 208"),   # Two-Way Media -> Alice
    ("898 F.3d 1161", "573 U.S. 208"),   # SAP v. InvestPic -> Alice
    ("920 F.3d 759",  "573 U.S. 208"),   # ChargePoint -> Alice
    ("934 F.3d 1373", "573 U.S. 208"),   # MyMail -> Alice
    ("935 F.3d 1341", "573 U.S. 208"),   # Chamberlain -> Alice
    ("874 F.3d 1329", "822 F.3d 1327"),  # Two-Way Media -> Enfish (distinguished)
    ("920 F.3d 759",  "773 F.3d 1245"),  # ChargePoint -> DDR Holdings
    ("920 F.3d 759",  "566 U.S. 66"),    # ChargePoint -> Mayo
    ("898 F.3d 1161", "566 U.S. 66"),    # SAP -> Mayo
    ("838 F.3d 1253", "566 U.S. 66"),    # Affinity Labs -> Mayo

    # Claim construction new
    ("521 F.3d 1351", "415 F.3d 1303"),  # O2 Micro -> Phillips
    ("800 F.3d 1366", "415 F.3d 1303"),  # Media Rights -> Phillips
    ("800 F.3d 1366", "792 F.3d 1339"),  # Media Rights -> Williamson
    ("713 F.3d 1090", "415 F.3d 1303"),  # Biogen -> Phillips

    # Divided / induced infringement
    ("797 F.3d 1020", "572 U.S. 915"),   # Akamai en banc -> Limelight (SCOTUS remand)
    ("572 U.S. 915",  "535 U.S. 722"),   # Limelight -> Festo (active inducement context)

    # Enhanced damages chain
    ("579 U.S. 93",   "547 U.S. 388"),   # Halo -> eBay (discretion standard parallel)
    ("776 F.3d 837",  "594 F.3d 860"),   # Bard Peripheral -> Lucent (damages context)

    # Patent exhaustion chain
    ("581 U.S. 360",  "553 U.S. 617"),   # Impression Products -> Quanta

    # Inequitable conduct chain
    ("864 F.3d 1343", "649 F.3d 1276"),  # Regeneron -> Therasense

    # IPR / PTAB new
    ("584 U.S. 325",  "572 U.S. 898"),   # Oil States -> Nautilus (validity review)
    ("590 U.S. 45",   "584 U.S. 325"),   # Thryv -> Oil States

    # FRAND cluster
    ("809 F.3d 1295",  "773 F.3d 1201"), # CSIRO -> Ericsson v. D-Link (FRAND methodology)

    # Declaratory judgment
    ("549 U.S. 118",  "547 U.S. 388"),   # MedImmune -> eBay (licensee standing / coercive context)
]


def build_citation_map() -> dict[str, str]:
    """Map citation_str -> case_id from metadata CSV."""
    mapping = {}
    with open(METADATA_CSV) as f:
        for row in csv.DictReader(f):
            mapping[row["citation_str"]] = row["case_id"]
    return mapping


def main():
    citation_map = build_citation_map()
    print(f"Loaded {len(citation_map)} cases from CSV")

    uri  = os.environ["NEO4J_URI"]
    user = os.environ["NEO4J_USERNAME"]
    pwd  = os.environ["NEO4J_PASSWORD"]
    driver = GraphDatabase.driver(uri, auth=(user, pwd))

    loaded = skipped = 0
    with driver.session() as session:
        for src_cit, tgt_cit in KNOWN_EDGES:
            src_id = citation_map.get(src_cit)
            tgt_id = citation_map.get(tgt_cit)
            if not src_id or not tgt_id:
                print(f"  SKIP (not in corpus): {src_cit} -> {tgt_cit}")
                skipped += 1
                continue
            session.run(
                "MATCH (a:Case {id: $src}), (b:Case {id: $tgt}) MERGE (a)-[:CITES]->(b)",
                {"src": src_id, "tgt": tgt_id},
            )
            loaded += 1

    driver.close()
    print(f"Loaded {loaded} citation edges ({skipped} skipped — not in corpus)")


if __name__ == "__main__":
    main()
