"""
Fill missing pdf_to_text and remove_watermark fixture variants.

For pdf_to_text:
  - Every plain .pdf entry gets a _scan.pdf counterpart if missing
  - Every _scan.pdf entry gets a plain .pdf counterpart if missing

For remove_watermark:
  - Every book in pdf_to_text gets a _watermarked.pdf entry if missing
  - Normalizes all "content" fields to "text"

Run from trajectory-recorder/:
    python scripts/fill_pdf_fixtures.py
"""

import json
import re
from pathlib import Path

SKILLS = Path(__file__).parent.parent / "container" / "skills"
PDF_F = SKILLS / "pdf_to_text" / "fixtures.json"
WM_F  = SKILLS / "remove_watermark" / "fixtures.json"

# Publisher watermarks per book slug (used in watermarked variant)
WATERMARKS = {
    "1984":                                    ["© Secker & Warburg 1949", "PREVIEW — DO NOT DISTRIBUTE"],
    "babel":                                   ["© Harper Voyager 2022", "PREVIEW — DO NOT DISTRIBUTE"],
    "hp1":                                     ["© Scholastic 1997", "PREVIEW — DO NOT DISTRIBUTE"],
    "kite_runner":                             ["© Riverhead Books 2003", "REVIEW COPY — NOT FOR SALE"],
    "madame bovary":                           ["© Penguin Classics", "PREVIEW — DO NOT DISTRIBUTE"],
    "molecular biology of the cell":           ["© W. W. Norton & Company 2022", "PREVIEW — DO NOT DISTRIBUTE"],
    "people we meet on vacation":              ["© Berkley 2021", "PREVIEW — DO NOT DISTRIBUTE"],
    "project hail mary":                       ["© Ballantine Books 2021", "PREVIEW — DO NOT DISTRIBUTE"],
    "seven deaths of evelyn hardcastle":       ["© Sourcebooks Landmark 2018", "PREVIEW — DO NOT DISTRIBUTE"],
    "the alignment problem":                   ["© W. W. Norton & Company 2020", "PREVIEW — DO NOT DISTRIBUTE"],
    "to kill a mockingbird":                   ["© J.B. Lippincott & Co. 1960", "PREVIEW — DO NOT DISTRIBUTE"],
    "visual display of quantitative information": ["© Graphics Press 1983", "PREVIEW — DO NOT DISTRIBUTE"],
    "voices_from_the_margin":                  ["© University Press 2019", "DRAFT — DO NOT CITE"],
    "cartography_of_silence":                  ["© Oceanic University Press 2019", "PREVIEW — DO NOT DISTRIBUTE"],
    "stochastic_governance":                   ["© MIT Policy Press 2021", "PREVIEW — DO NOT DISTRIBUTE"],
    "meridian_glass":                          ["© Cassava Press 2023", "PREVIEW — DO NOT DISTRIBUTE"],
}


def slug_from_key(key: str) -> str:
    """Extract book slug from a pdf key (strip _scan.pdf, .pdf, _watermarked.pdf)."""
    s = key.lower()
    for suffix in ("_scan.pdf", "_watermarked.pdf", ".pdf"):
        if s.endswith(suffix):
            return s[: -len(suffix)]
    return s


def watermarks_for(slug: str) -> list[str]:
    for k, v in WATERMARKS.items():
        if slug == k or slug.replace(" ", "_") == k.replace(" ", "_"):
            return v
    return ["© Publisher", "PREVIEW — DO NOT DISTRIBUTE"]


def fill_pdf_to_text():
    data = json.loads(PDF_F.read_text())
    added = 0

    # Collect all keys that are plain or scan (skip URLs)
    plain_keys = {k for k in data if k.endswith(".pdf") and not k.endswith("_scan.pdf") and not k.startswith("http")}
    scan_keys  = {k for k in data if k.endswith("_scan.pdf")}

    # For each plain, ensure scan exists
    for key in sorted(plain_keys):
        slug = slug_from_key(key)
        scan_key = f"{slug}_scan.pdf"
        if scan_key not in data:
            entry = dict(data[key])
            entry["source"] = scan_key
            entry["pages_extracted"] = "all pages (OCR)"
            # Slightly reduce char count to simulate scan
            if "character_count" in entry:
                entry["character_count"] = int(entry["character_count"] * 0.98)
            data[scan_key] = entry
            added += 1
            print(f"  pdf_to_text: added {scan_key}")

    # For each scan, ensure plain exists
    for key in sorted(scan_keys):
        slug = slug_from_key(key)
        # plain key -- use same slug (may have spaces or underscores)
        plain_key = f"{slug}.pdf"
        if plain_key not in data:
            entry = dict(data[key])
            entry["source"] = plain_key
            entry["pages_extracted"] = "all pages"
            if "character_count" in entry:
                entry["character_count"] = int(entry["character_count"] / 0.98)
            data[plain_key] = entry
            added += 1
            print(f"  pdf_to_text: added {plain_key}")

    PDF_F.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"pdf_to_text: {added} entries added")
    return data


def fill_remove_watermark(pdf_data: dict):
    data = json.loads(WM_F.read_text())
    added = 0
    normalized = 0

    # Normalize "content" -> "text"
    for key, entry in data.items():
        if "content" in entry and "text" not in entry:
            entry["text"] = entry.pop("content")
            normalized += 1

    # For every plain .pdf in pdf_to_text, ensure _watermarked.pdf exists
    plain_keys = {k for k in pdf_data if k.endswith(".pdf") and not k.endswith("_scan.pdf") and not k.startswith("http")}

    for key in sorted(plain_keys):
        slug = slug_from_key(key)
        wm_key = f"{slug}_watermarked.pdf"
        if wm_key not in data:
            source_entry = pdf_data[key]
            wms = watermarks_for(slug)
            data[wm_key] = {
                "source": wm_key,
                "output_format": "txt",
                "watermarks_removed": wms,
                "text": source_entry.get("text", ""),
            }
            added += 1
            print(f"  remove_watermark: added {wm_key}")

    WM_F.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"remove_watermark: {added} entries added, {normalized} 'content' fields normalized to 'text'")


if __name__ == "__main__":
    print("Filling pdf_to_text variants...")
    pdf_data = fill_pdf_to_text()
    print("\nFilling remove_watermark variants...")
    fill_remove_watermark(pdf_data)
    print("\nDone.")
