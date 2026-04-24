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

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}

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

def detect_language(text: str) -> str:
    if len(text.strip()) < 20:
        return "unknown"
    try:
        return detect(text)
    except Exception:
        return "unknown"

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

def build_filename(index: int, doc_type: str, lang: str, date_str: str) -> str:
    date_clean = clean_filename_part(date_str, max_len=20)
    return f"{index:02d}_{doc_type}_{lang}_{date_clean}"

def process_file(file_path: Path, index: int):
    ext = file_path.suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        print(f"Übersprungen (nicht unterstützt): {file_path.name}")
        return

    print(f"\nVerarbeite: {file_path.name}")

    if ext == ".pdf":
        text = extract_text_from_pdf(file_path)
    else:
        text = extract_text_from_image(file_path)

    lang = detect_language(text)
    doc_type = guess_document_type(text)
    date_str = guess_date(text)

    new_name = build_filename(index, doc_type, lang, date_str) + ext
    target_path = OUTPUT / new_name

    # falls Name schon existiert
    counter = 1
    while target_path.exists():
        target_path = OUTPUT / f"{build_filename(index, doc_type, lang, date_str)}_{counter}{ext}"
        counter += 1

    shutil.move(str(file_path), str(target_path))

    log_file = LOGS / f"{target_path.stem}.txt"
    preview = text[:1500] if text else "(kein Text erkannt)"
    log_file.write_text(
        f"Original: {file_path.name}\n"
        f"Neu: {target_path.name}\n"
        f"Sprache: {lang}\n"
        f"Dokumenttyp: {doc_type}\n"
        f"Datum: {date_str}\n\n"
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
