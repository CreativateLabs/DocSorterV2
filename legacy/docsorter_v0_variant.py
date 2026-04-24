from pathlib import Path
import shutil
import re
from datetime import datetime

import pytesseract
from pypdf import PdfReader
from pdf2image import convert_from_path
from PIL import Image
from langdetect import detect, DetectorFactory
from slugify import slugify
import docx

DetectorFactory.seed = 0

BASE = Path.home() / "Documents" / "DocSorter"
INPUT = BASE / "input"
OUTPUT = BASE / "output"
LOGS = BASE / "logs"

# OCR-Sprachen:
# eng = Englisch
# deu = Deutsch
# sqi = Albanisch
OCR_LANGS = "eng+deu+sqi"

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".docx"}

def clean_filename_part(text: str, max_len: int = 40) -> str:
    text = text.strip() if text else "unbekannt"
    text = re.sub(r"\s+", " ", text)
    text = slugify(text, separator="_")
    if not text:
        text = "unbekannt"
    return text[:max_len]

def extract_text_from_pdf(pdf_path: Path) -> str:
    text = ""
    try:
        reader = PdfReader(str(pdf_path))
        for page in reader.pages[:5]:
            text += (page.extract_text() or "") + "\n"
    except Exception:
        pass

    # Fallback auf OCR, wenn kaum Text gefunden wurde
    if len(text.strip()) < 30:
        try:
            images = convert_from_path(str(pdf_path), dpi=200, first_page=1, last_page=3)
            ocr_text = []
            for img in images:
                ocr_text.append(pytesseract.image_to_string(img, lang=OCR_LANGS))
            text = "\n".join(ocr_text)
        except Exception:
            pass

    return text.strip()

def extract_text_from_image(image_path: Path) -> str:
    try:
        img = Image.open(image_path)
        return pytesseract.image_to_string(img, lang=OCR_LANGS).strip()
    except Exception:
        return ""
def extract_text_from_docx(docx_path: Path) -> str:
    try:
        document = docx.Document(str(docx_path))
        paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
        return "\n".join(paragraphs).strip()
    except Exception:
        return ""

def detect_language(text: str) -> str:
    if len(text.strip()) < 20:
        return "unknown"
    try:
        return detect(text)
    except Exception:
        return "unknown"

def guess_partner(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    patterns = [
        r"(kunde|customer|client|vertragspartner|partner)[:\s]+(.+)",
        r"(firma|company)[:\s]+(.+)",
    ]

    for line in lines[:15]:
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                value = match.group(2).strip()
                return clean_filename_part(value, max_len=40)

    return "unbekannt"

def guess_country(text: str) -> str:
    t = text.lower()

    country_map = {
        "deutschland": "deutschland",
        "germany": "deutschland",
        "kosovo": "kosovo",
        "kosova": "kosovo",
        "albania": "albanien",
        "albanien": "albanien",
        "england": "england",
        "united kingdom": "england",
        "uk": "england",
        "vereinigtes königreich": "england",
        "usa": "usa",
        "united states": "usa",
        "österreich": "oesterreich",
        "austria": "oesterreich",
        "schweiz": "schweiz",
        "switzerland": "schweiz",
    }

    for key, value in country_map.items():
        if key in t:
            return value

    return "unbekannt"

def is_uncertain(text: str, partner: str, country: str, doc_type: str) -> bool:
    if len(text.strip()) < 30:
        return True
    if partner == "unbekannt":
        return True
    if country == "unbekannt":
        return True
    if doc_type == "dokument":
        return True
    return False

def guess_document_type(text: str) -> str:
    t = text.lower()

    if any(word in t for word in ["rechnung", "invoice", "fature"]):
        return "rechnung"
    if any(word in t for word in ["vertrag", "contract", "agreement", "kontrate"]):
        return "vertrag"
    if any(word in t for word in ["angebot", "offer", "quotation"]):
        return "angebot"
    if any(word in t for word in ["mahnung", "reminder", "forderung", "debt"]):
        return "mahnung"
    if any(word in t for word in ["brief", "letter"]):
        return "brief"

    return "dokument"

def guess_date(text: str) -> str:
    patterns = [
        r"\b(\d{2}\.\d{2}\.\d{4})\b",
        r"\b(\d{2}\.\d{2}\.\d{2})\b",
        r"\b(\d{4}-\d{2}-\d{2})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return datetime.now().strftime("%d.%m.%Y")

def build_filename(doc_type: str, partner: str, country: str, date_str: str) -> str:
    doc_type_clean = clean_filename_part(doc_type, max_len=30)
    partner_clean = clean_filename_part(partner, max_len=40)
    country_clean = clean_filename_part(country, max_len=30)
    date_clean = clean_filename_part(date_str, max_len=20)

    return f"{doc_type_clean}_{partner_clean}_{country_clean}_{date_clean}"


def process_file(file_path: Path, index: int):
    ext = file_path.suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        print(f"Übersprungen (nicht unterstützt): {file_path.name}")
        return

    print(f"\nVerarbeite: {file_path.name}")

    if ext == ".pdf":
        text = extract_text_from_pdf(file_path)
    elif ext == ".docx":
        text = extract_text_from_docx(file_path)
    else:
        text = extract_text_from_image(file_path)

    lang = detect_language(text)
    doc_type = guess_document_type(text)
    date_str = guess_date(text)
    partner = guess_partner(text)
    country = guess_country(text)
    uncertain = is_uncertain(text, partner, country, doc_type)

    new_name = build_filename(doc_type, partner, country, date_str) + ext

    if uncertain:
        target_folder = OUTPUT / "_review" / doc_type
    else:
        target_folder = OUTPUT / doc_type / country / partner

    target_folder.mkdir(parents=True, exist_ok=True)
    target_path = target_folder / new_name

    counter = 1
    while target_path.exists():
        target_path = target_folder / f"{build_filename(doc_type, partner, country, date_str)}_{counter}{ext}"
        counter += 1

    shutil.move(str(file_path), str(target_path))

    log_file = LOGS / f"{target_path.stem}.txt"
    preview = text[:1500] if text else "(kein Text erkannt)"
    log_file.write_text(
        f"Original: {file_path.name}\n"
        f"Neu: {target_path.name}\n"
        f"Sprache: {lang}\n"
        f"Dokumenttyp: {doc_type}\n"
        f"Partner: {partner}\n"
        f"Land: {country}\n"
        f"Datum: {date_str}\n"
        f"Unsicher: {uncertain}\n\n"
        f"--- Textvorschau ---\n{preview}\n",
        encoding="utf-8"
    )

    print(f"Neu benannt: {target_path.name}")
    print(f"Verschoben nach: {target_path}")
    print(f"Log erstellt: {log_file.name}")

def main():
    INPUT.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)

    files = sorted([f for f in INPUT.iterdir() if f.is_file()])[:10]

    if not files:
        print("Keine Dateien im input-Ordner gefunden.")
        return

    for idx, file_path in enumerate(files, start=1):
        process_file(file_path, idx)

    print("\nFertig. Schau jetzt im Finder in:")
    print(f"Input:  {INPUT}")
    print(f"Output: {OUTPUT}")
    print(f"Logs:   {LOGS}")

if __name__ == "__main__":
    main()
