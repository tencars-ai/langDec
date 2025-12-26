import csv
import re
import sys
import xml.etree.ElementTree as ET


def localname(tag: str) -> str:
    """Return tag name without XML namespace."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def normalize_spaces(text: str) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", (text or "").strip())


def text_with_spaces(elem: ET.Element) -> str:
    """
    Extract text from an XML element, ensuring that multi-part phrases
    are joined with spaces (TEI often splits text into multiple nodes).

    Also cleans up spacing around common punctuation.
    """
    parts = [p.strip() for p in elem.itertext() if p and p.strip()]
    text = " ".join(parts)

    # Remove spaces before punctuation: "word ," -> "word,"
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)

    # Remove spaces after opening brackets: "( word" -> "(word"
    text = re.sub(r"(\()\s+", r"\1", text)

    # Collapse repeated spaces again, just in case
    text = re.sub(r"\s{2,}", " ", text).strip()

    return text


def extract_headwords(entry_elem: ET.Element) -> list[str]:
    """
    Extract headwords from common FreeDict TEI structures:
      - Prefer: <form type="lemma"><orth>...</orth></form>
      - Fallback: any <orth> inside the entry

    Returns a list because entries can contain multiple orthographic forms.
    """
    headwords: list[str] = []

    # Prefer lemma forms
    for form in entry_elem.iter():
        if localname(form.tag) != "form":
            continue
        form_type = (form.attrib.get("type") or "").lower()
        if form_type != "lemma":
            continue

        for orth in form.iter():
            if localname(orth.tag) == "orth":
                hw = normalize_spaces(text_with_spaces(orth))
                if hw:
                    headwords.append(hw)

    # Fallback: any orth in entry
    if not headwords:
        for orth in entry_elem.iter():
            if localname(orth.tag) == "orth":
                hw = normalize_spaces(text_with_spaces(orth))
                if hw:
                    headwords.append(hw)

    # Deduplicate while preserving order (case-insensitive)
    seen = set()
    unique: list[str] = []
    for hw in headwords:
        key = hw.lower()
        if key not in seen:
            seen.add(key)
            unique.append(hw)

    return unique


def extract_translations(entry_elem: ET.Element) -> list[str]:
    """
    Extract translations from TEI. Typical FreeDict TEI uses:
      - <cit type="trans"><quote>...</quote></cit>

    We extract all <quote> under <cit type="trans">.
    """
    translations: list[str] = []

    for cit in entry_elem.iter():
        if localname(cit.tag) != "cit":
            continue
        cit_type = (cit.attrib.get("type") or "").lower()
        if cit_type != "trans":
            continue

        for quote in cit.iter():
            if localname(quote.tag) == "quote":
                tr = normalize_spaces(text_with_spaces(quote))
                if tr:
                    translations.append(tr)

    # Deduplicate while preserving order (case-insensitive)
    seen = set()
    unique: list[str] = []
    for tr in translations:
        key = tr.lower()
        if key not in seen:
            seen.add(key)
            unique.append(tr)

    return unique


def convert_tei_to_tsv(input_tei_path: str, output_tsv_path: str) -> None:
    """
    Convert a FreeDict TEI file to a TSV file with:
      headword<TAB>translation

    Writes every combination of (headword, translation) for each entry.
    """
    tree = ET.parse(input_tei_path)
    root = tree.getroot()

    rows_written = 0
    entries_skipped = 0

    with open(output_tsv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")

        for elem in root.iter():
            if localname(elem.tag) != "entry":
                continue

            headwords = extract_headwords(elem)
            translations = extract_translations(elem)

            if not headwords or not translations:
                entries_skipped += 1
                continue

            for hw in headwords:
                for tr in translations:
                    writer.writerow([hw, tr])
                    rows_written += 1

    print(f"Done. Rows written: {rows_written}, skipped entries: {entries_skipped}")


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python scripts/convert_freedict_tei_to_tsv.py <input.tei> <output.tsv>")
        return 2

    input_tei_path = sys.argv[1]
    output_tsv_path = sys.argv[2]

    convert_tei_to_tsv(input_tei_path, output_tsv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
