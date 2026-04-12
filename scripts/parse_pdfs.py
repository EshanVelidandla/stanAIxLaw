"""
Parse PDF documents (MPEP chapters, USPTO guidance) using LlamaParse.
Output: /data/parsed_docs/{filename}.md

Usage: python scripts/parse_pdfs.py [optional: path/to/file.pdf ...]

If no arguments, parses all PDFs in /data/raw/pdfs/
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
PDF_DIR = DATA_DIR / "raw" / "pdfs"
OUT_DIR = DATA_DIR / "parsed_docs"
PDF_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_with_llamaparse(pdf_path: Path) -> str:
    from llama_parse import LlamaParse
    api_key = os.environ.get("LLAMA_CLOUD_API_KEY")
    if not api_key:
        raise RuntimeError("LLAMA_CLOUD_API_KEY not set in .env")
    parser = LlamaParse(result_type="markdown", api_key=api_key)
    docs = parser.load_data(str(pdf_path))
    return "\n\n".join(d.text for d in docs)


def main():
    if len(sys.argv) > 1:
        pdf_paths = [Path(p) for p in sys.argv[1:]]
    else:
        pdf_paths = list(PDF_DIR.glob("*.pdf"))
        if not pdf_paths:
            print(f"No PDFs found in {PDF_DIR}")
            print("Place MPEP chapter PDFs there, or run with explicit paths.")
            print("Recommended: MPEP chapters 2100, 2200, 700 from USPTO website.")
            return

    for pdf_path in pdf_paths:
        out_path = OUT_DIR / (pdf_path.stem + ".md")
        if out_path.exists():
            print(f"  Skipping {pdf_path.name} (already parsed)")
            continue
        print(f"  Parsing {pdf_path.name}…")
        try:
            markdown = parse_with_llamaparse(pdf_path)
            out_path.write_text(markdown, encoding="utf-8")
            print(f"    -> {out_path} ({len(markdown)} chars)")
        except Exception as e:
            print(f"    ERROR: {e}")

    print("Done.")


if __name__ == "__main__":
    main()
