"""
invoice_extractor.py
Vendor-agnostic Faktur Pajak OCR pipeline.
Drop all PDFs into a folder, run this script, get extracted_invoice_data.xlsx.

Usage:
    python invoice_extractor.py "C:/path/to/pdf/folder"
    python invoice_extractor.py  # uses default folder

Dependencies:
    pip install pdfplumber pandas openpyxl
    pip install pytesseract pillow numpy opencv-python  # optional OCR fallback
"""

import os
import re
import glob
import pdfplumber
import pandas as pd
from datetime import datetime

# ============================================================================
# CONFIG
# ============================================================================

OUTPUT_COLUMNS = [
    "Filename",
    "Vendor",
    "Reference PO",
    "Invoice No",
    "Invoice Date",
    "Due Date",
    "Tax Invoice No",
    "PPN",
    "Total Transaction",
    "Deskripsi",
]

VENDOR_MAP = {
    "INDOINTERNET": "PT. Indointernet",
    "PT. INDOINTERNET": "PT. Indointernet",
    "PT. IndoInternet": "PT. Indointernet",
    "CENDIKIA GLOBAL SOLUSI": "PT. Cendikia Global Solusi",
    "PT. CENDIKIA GLOBAL SOLUSI": "PT. Cendikia Global Solusi",
    "PT. Cendikia Global Solusi": "PT. Cendikia Global Solusi",
    "FIBER MEDIA INDONESIA": "PT. Fiber Media Indonesia",
    "PT. FIBER MEDIA INDONESIA": "PT. Fiber Media Indonesia",
    "PT. Fiber Media Indonesia": "PT. Fiber Media Indonesia",
    "KAWAN LAMA SEJAHTERA": "PT. Kawan Lama Sejahtera",
    "PT. KAWAN LAMA SEJAHTERA": "PT. Kawan Lama Sejahtera",
    "PT. Kawan Lama Sejahtera": "PT. Kawan Lama Sejahtera",
    "MELVAR PRIMA SOLUSI": "PT. Melvar Prima Solusi",
    "PT. MELVAR PRIMA SOLUSI": "PT. Melvar Prima Solusi",
    "PT. Melvar Prima Solusi": "PT. Melvar Prima Solusi",
    "MAXINDO MITRA SOLUSI": "PT. Maxindo Mitra Solusi",
    "PT. MAXINDO MITRA SOLUSI": "PT. Maxindo Mitra Solusi",
    "PT. Maxindo Mitra Solusi": "PT. Maxindo Mitra Solusi",
    "PT. Iforte Solusi Infotek": "PT. Iforte Solusi Infotek",
    "PT. BIT TEKNOLOGI NUSANTARA": "PT. Bit Teknologi Nusantara",
    "PT. Bit Teknologi Nusantara": "PT. Bit Teknologi Nusantara",
    "PT. Data Utama Dinamika": "PT. Data Utama Dinamika",
}

VENDOR_PO_MAP = {
    "PT. Indointernet": "LK000011",
    "PT. Cendikia Global Solusi": "TL000013",
    "PT. Fiber Media Indonesia": "LK000086",
    "PT. Kawan Lama Sejahtera": "SP000138",
    "PT. Melvar Prima Solusi": "SP000445",
    "PT. Maxindo Mitra Solusi": "SP000400",
    "PT. Iforte Solusi Infotek": "TL000008",
    "PT. Bit Teknologi Nusantara": "LK000043",
    "PT. Data Utama Dinamika": "LK000043",
}

FILENAME_VENDOR_PATTERNS = [
    (r"PT\.?\s*Indointernet", "PT. Indointernet"),
    (r"PT\.?\s*Cendikia\s*Global\s*Solusi", "PT. Cendikia Global Solusi"),
    (r"PT\.?\s*Fiber\s*Media\s*Indonesia", "PT. Fiber Media Indonesia"),
    (r"PT\.?\s*Kawan\s*Lama\s*Sejahtera", "PT. Kawan Lama Sejahtera"),
    (r"PT\.?\s*Melvar\s*Prima\s*Solusi", "PT. Melvar Prima Solusi"),
    (r"PT\.?\s*Maxindo\s*Mitra\s*Solusi", "PT. Maxindo Mitra Solusi"),
    (r"PT\.?\s*Iforte\s*Solusi\s*Infotek", "PT. Iforte Solusi Infotek"),
    (r"PT\.?\s*Bit\s*Teknologi\s*Nusantara", "PT. Bit Teknologi Nusantara"),
    (r"PT\.?\s*Data\s*Utama\s*Dinamika", "PT. Data Utama Dinamika"),
]


# ============================================================================
# TEXT UTILS
# ============================================================================

def clean_number(text):
    if not text:
        return 0.0
    cleaned_text = re.sub(r"[^\d,.-]", "", text).strip()
    try:
        if "," in cleaned_text and "." in cleaned_text:
            if cleaned_text.rfind(",") > cleaned_text.rfind("."):
                cleaned_text = cleaned_text.replace(".", "").replace(",", ".")
            else:
                cleaned_text = cleaned_text.replace(",", "")
        elif "." in cleaned_text and "," not in cleaned_text:
            cleaned_text = cleaned_text.replace(".", "")
        elif "," in cleaned_text:
            if len(cleaned_text.split(",")[-1]) <= 2:
                cleaned_text = cleaned_text.replace(",", ".")
            else:
                cleaned_text = cleaned_text.replace(",", "")
        return float(cleaned_text)
    except (ValueError, TypeError):
        return 0.0


def format_currency(value):
    try:
        value = float(value)
        formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except (ValueError, TypeError):
        return "0,00"


# ============================================================================
# FILE UTILS
# ============================================================================

def clean_text(text):
    text = text.replace("|", "I")
    text = text.replace("\r", " ")
    text = re.sub(r"[\x0c]", " ", text)
    text = re.sub(r"[^a-zA-Z0-9./:\-\s,()]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_spaces(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def detect_vendor_from_filename(filename):
    filename_upper = filename.upper()
    for pattern, vendor in FILENAME_VENDOR_PATTERNS:
        if re.search(pattern, filename_upper, re.IGNORECASE):
            return vendor
    return None


def extract_invoice_no_from_filename(filename):
    patterns = [
        r"(?:INV[./-])?(\d{3}[./-]\d{4}[./-]\d{10}[./-]\d{3})",
        r"(?:INV[./-])?([A-Z]+-\d{4}[./-]\d{2}[./-]\d{2}[./-]\d{2})",
        r"(\d{4}/[A-Z]+-INV/[A-Z]+/\d{5})",
        r"(KL\d{10})",
        r"(MPS/\d{4}/\d{2}/\d{4})",
        r"(DUD-\d{4}-\d{2}-\d{5})",
        r"(MMS/INV\d{8})",
        r"(IASS/INV[A-Z]+/\d{4}/\d{6})",
        r"([A-Z]+/INV/\d{4}/\d{6})",
    ]
    filename_upper = filename.upper()
    for pattern in patterns:
        match = re.search(pattern, filename_upper, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


# ============================================================================
# INVOICE INFO EXTRACTION
# ============================================================================

BULAN_MAP = {
    "januari": "January", "februari": "February", "maret": "March",
    "april": "April", "mei": "May", "juni": "June",
    "juli": "July", "agustus": "August", "september": "September",
    "oktober": "October", "november": "November", "desember": "December",
}


def extract_invoice_no(text):
    match = re.search(r"Referensi:\s*([A-Za-z0-9/\-.\s]{4,50}?)(?=\s*[,.]?\s*Pemberitahuan|\s*\n\s*Pemberitahuan|$)", text, re.IGNORECASE)
    if not match:
        match = re.search(r"Referensi:\s*([A-Za-z0-9/\-.]{4,50}?)(?:\s*\)|\s*[,.\-]?\s*(?:Pemberitahuan|Tanggal))", text, re.IGNORECASE)
    if not match:
        match = re.search(r"(?:Referensi|No\.?\s*Tagihan)[:\s]*([A-Za-z0-9/\-.\s]{4,50}?)(?=\s*Pemberitahuan|\s*Ditandatangani|$)", text, re.IGNORECASE)
    if not match:
        match = re.search(r"(?:Referensi|No\.?\s*Tagihan)[:\s]*([A-Za-z0-9/\-.\s]{4,50})", text, re.IGNORECASE)

    if match:
        raw = match.group(1).strip()
        raw = re.sub(r"^\s*[-:.)]+\s*", "", raw)
        raw = re.sub(r"\s+", " ", raw).strip()
        raw = re.sub(r"[,.\-\s]+$", "", raw)
        if raw and len(raw) > 3:
            return raw
    return "NOT FOUND"


def extract_invoice_date(text):
    bulan_list = "|".join(BULAN_MAP.keys())
    pola_tanggal = rf"KOTA\s+[A-Z\s.,]+,\s+(\d{{1,2}})\s+({bulan_list})\s+(\d{{4}})"
    match = re.search(pola_tanggal, text, re.IGNORECASE)
    if match:
        hari, bulan, tahun = match.groups()
        bulan_inggris = BULAN_MAP.get(bulan.lower())
        if bulan_inggris:
            try:
                tanggal_obj = datetime.strptime(f"{hari} {bulan_inggris} {tahun}", "%d %B %Y")
                return tanggal_obj.strftime("%Y-%m-%d")
            except ValueError:
                pass

    fallback = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
    if fallback:
        try:
            return datetime.strptime(fallback.group(0).replace("/", "-"), "%d-%m-%Y").strftime("%Y-%m-%d")
        except ValueError:
            pass

    return "NOT FOUND"


# ============================================================================
# TAX INFO EXTRACTION
# ============================================================================

def extract_tax_invoice_no(text):
    match = re.search(r"(?:Kode\s+dan\s+Nomer?\s+Seri\s+Faktur\s*Pajak|Seri\s*Faktur\s*Pajak|Nomor\s+Seri\s+Faktur\s*Pajak)[:.\s]*(\d{15,17})", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "NOT FOUND"


def extract_dpp(text):
    match = re.search(r"Dasar\s+Pengenaan\s+Pajak\s+([\d.,]+)", text, re.IGNORECASE)
    if match:
        return clean_number(match.group(1))
    all_nums = re.findall(r"([\d.]{1,3}(?:\.\d{3}){2,})", text)
    candidates = [clean_number(n) for n in all_nums if clean_number(n) > 100_000]
    if candidates:
        return max(candidates)
    return 0.0


def extract_ppn(text, dpp=0.0):
    ppn_match = re.search(r"Jumlah\s+PPN\s*(?:\(Pajak\s*Pertambahan\s*Nilai\))?\s*([\d.,]+)", text, re.IGNORECASE)
    if ppn_match:
        return clean_number(ppn_match.group(1))

    if dpp > 0:
        harga_match = re.search(r"Harga\s+Jual\s*/\s*Penggantian\s*/\s*Uang\s*Muka\s*/\s*Termin\s+([\d.,]+)", text, re.IGNORECASE)
        if harga_match:
            harga = clean_number(harga_match.group(1))
            if harga > dpp:
                return harga - dpp
        ppn_calc = round(dpp * 0.11)
        if abs(ppn_calc - (dpp * 0.11)) < (dpp * 0.02):
            return ppn_calc

    return 0.0


def extract_vendor_name(text):
    match = re.search(r"(?:Pengusaha\s+Kena\s+Pajak|Nama\s*:)\s*\n?\s*Nama\s*:\s*([A-Z][A-Z\s&\.\-,]+?)(?:\n|Alamat|NPWP|$)", text, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        name = re.sub(r"\s+", " ", name)
        return name

    match2 = re.search(r"(?:Faktur\s*Pajak\s*\n|Nama:\s*)([A-Z][A-Z\s&\.\-,]{5,60}?)(?:\n|$)", text, re.IGNORECASE)
    if match2:
        name = match2.group(1).strip()
        return re.sub(r"\s+", " ", name)

    return "NOT FOUND"


def extract_vendor_npwp(text):
    matches = re.findall(r"(?:Pengusaha\s+Kena\s+Pajak|Nama\s*:)[^N]*(?:NPWP|Alamat)[^#]*#?(\d{13,15})", text, re.IGNORECASE)
    for m in matches:
        digits = re.sub(r"\D", "", m)
        if len(digits) >= 13:
            return digits[:13]
    match = re.search(r"NPWP\s*:\s*(\d{13,15})", text, re.IGNORECASE)
    if match:
        return re.sub(r"\D", "", match.group(1))[:13]
    return "NOT FOUND"


def extract_buyer_npwp(text):
    match = re.search(r"(?:Pembeli\s*Barang\s*Kena\s*Pajak|Penerima\s*Jasa)[^N]*(?:NPWP)[^#]*#?(\d{13,15})", text, re.IGNORECASE)
    if match:
        return re.sub(r"\D", "", match.group(1))[:13]
    buyer_block_match = re.search(r"Pembeli\s*Barang[^\n]*\n([\s\S]*?)(?:Email|Identitas)", text, re.IGNORECASE)
    if buyer_block_match:
        npwp_match = re.search(r"NPWP\s*:\s*(\d{13,15})", buyer_block_match.group(1))
        if npwp_match:
            return re.sub(r"\D", "", npwp_match.group(1))[:13]
    return "NOT FOUND"


# ============================================================================
# DESCRIPTION EXTRACTION
# ============================================================================

def extract_description(text):
    lines = text.strip().split("\n")

    header_pattern = re.compile(
        r"No\.\s*Barang\s*/\s*Nama\s*Barang\s*Kena\s*Pajak\s*/\s*Jasa\s*Kena\s*Pajak\s*Uang\s*Muka\s*/\s*Termin",
        re.IGNORECASE,
    )
    price_pattern = re.compile(r"Rp\s+[\d.,]+\s+x\s+[\d.,]+\s+(?:Bulan|Lainnya)", re.IGNORECASE)

    header_idx = None
    price_idx = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if header_pattern.search(stripped):
            header_idx = i
        elif price_pattern.search(stripped):
            price_idx = i

    if header_idx is None or price_idx is None:
        return "NOT FOUND"

    if price_idx <= header_idx + 1:
        return "NOT FOUND"

    between = lines[header_idx + 1 : price_idx]
    combined = " ".join(l.strip() for l in between if l.strip())
    combined = re.sub(r"\s+", " ", combined).strip()

    if len(combined) > 0:
        return combined
    return "NOT FOUND"


# ============================================================================
# PDF SCANNER
# ============================================================================

def find_faktur_pajak_page(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if "Faktur Pajak" in text and "Kode dan Nomor Seri" in text:
                return page_num, page
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if "Faktur Pajak" in text and ("Nama :" in text or "Nama:" in text) and "NPWP" in text:
                return page_num, page
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if "Faktur Pajak" in text:
                return page_num, page
    return None, None


def extract_fp_text(pdf_path):
    page_num, page = find_faktur_pajak_page(pdf_path)
    if page is None:
        return ""

    texts = [page.extract_text() or ""]

    with pdfplumber.open(pdf_path) as pdf:
        for i in range(page_num + 1, len(pdf.pages)):
            next_text = pdf.pages[i].extract_text() or ""
            if not next_text.strip():
                break
            if re.search(r"^\s*Faktur\s*Pajak", next_text, re.MULTILINE):
                break
            texts.append(next_text)

    return "\n".join(texts)


def get_page_texts(pdf_path):
    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            texts.append(text)
    return texts


def render_page_to_image(pdf_path, page_num=0, dpi=200):
    import fitz
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")
    doc.close()
    return img_bytes


# ============================================================================
# OCR PROCESSOR (optional fallback)
# ============================================================================

def get_tesseract_lang():
    return "ind"


def preprocess_image(img_bytes):
    import numpy as np
    import cv2
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    return thresh


def ocr_image(img_bytes, lang="ind"):
    try:
        import pytesseract
        import numpy as np
        import cv2
        thresh = preprocess_image(img_bytes)
        text = pytesseract.image_to_string(thresh, lang=lang, config="--psm 6")
        return text
    except ImportError:
        return None


def ocr_pdf_page(pdf_path, page_num=0):
    img_bytes = render_page_to_image(pdf_path, page_num)
    text = ocr_image(img_bytes)
    return text


# ============================================================================
# MAIN PROCESSOR
# ============================================================================

def extract_all_fields(text, filename="", use_ocr_fallback=False):
    cleaned = clean_text(text)

    invoice_no = extract_invoice_no(cleaned)
    if invoice_no == "NOT FOUND":
        invoice_no = extract_invoice_no_from_filename(filename)

    invoice_date = extract_invoice_date(cleaned)
    tax_invoice_no = extract_tax_invoice_no(cleaned)
    dpp = extract_dpp(cleaned)
    ppn = extract_ppn(cleaned, dpp)
    description = extract_description(text)
    vendor_name_raw = extract_vendor_name(cleaned)
    vendor_npwp = extract_vendor_npwp(cleaned)

    vendor_from_fp = VENDOR_MAP.get(vendor_name_raw.upper()) or VENDOR_MAP.get(vendor_name_raw)
    vendor_from_filename = detect_vendor_from_filename(filename)

    if vendor_from_fp:
        vendor_name = vendor_from_fp
    elif vendor_from_filename:
        vendor_name = vendor_from_filename
    else:
        vendor_name = vendor_name_raw if vendor_name_raw != "NOT FOUND" else "NOT FOUND"

    vendor_po = VENDOR_PO_MAP.get(vendor_name, "NOT FOUND")

    return {
        "Filename": filename,
        "Vendor": vendor_name,
        "Reference PO": vendor_po,
        "Invoice No": invoice_no,
        "Invoice Date": invoice_date,
        "Due Date": "NOT FOUND",
        "Tax Invoice No": tax_invoice_no,
        "PPN": format_currency(ppn),
        "Total Transaction": format_currency(dpp),
        "Deskripsi": description,
        "_vendor_npwp": vendor_npwp,
        "_buyer_npwp": extract_buyer_npwp(cleaned),
        "_ocr_used": use_ocr_fallback,
    }


def result_is_poor(result):
    not_found_count = sum(
        1 for k, v in result.items()
        if v == "NOT FOUND" and k not in ["Due Date", "_vendor_npwp", "_buyer_npwp", "_ocr_used"]
    )
    return not_found_count >= 3


def count_valid_fields(result):
    return sum(
        1 for k, v in result.items()
        if v not in ["NOT FOUND", "", "0,00"] and not k.startswith("_")
    )


def process_pdf(pdf_path, use_ocr=True):
    filename = os.path.basename(pdf_path)
    fp_text = extract_fp_text(pdf_path)

    if not fp_text:
        return make_empty_result(filename)

    result = extract_all_fields(fp_text, filename, use_ocr_fallback=False)

    if use_ocr and result_is_poor(result):
        page_num, _ = find_faktur_pajak_page(pdf_path)
        if page_num is not None:
            ocr_text = ocr_pdf_page(pdf_path, page_num)
            if ocr_text:
                result_ocr = extract_all_fields(ocr_text, filename, use_ocr_fallback=True)
                if count_valid_fields(result_ocr) > count_valid_fields(result):
                    result = result_ocr

    return result


def make_empty_result(filename):
    return {
        "Filename": filename,
        "Vendor": "NOT FOUND",
        "Reference PO": "NOT FOUND",
        "Invoice No": "NOT FOUND",
        "Invoice Date": "NOT FOUND",
        "Due Date": "NOT FOUND",
        "Tax Invoice No": "NOT FOUND",
        "PPN": "0,00",
        "Total Transaction": "0,00",
        "Deskripsi": "NOT FOUND",
        "_vendor_npwp": "NOT FOUND",
        "_buyer_npwp": "NOT FOUND",
        "_ocr_used": False,
    }


# ============================================================================
# EXCEL WRITER
# ============================================================================

def write_excel(results, output_path, folder_path):
    df = pd.DataFrame(results)
    cols_present = [c for c in OUTPUT_COLUMNS if c in df.columns]
    df = df[cols_present]
    try:
        df.to_excel(output_path, index=False, engine="openpyxl")
    except PermissionError:
        backup_path = os.path.join(folder_path, "extracted_invoice_data_v2.xlsx")
        df.to_excel(backup_path, index=False, engine="openpyxl")
        output_path = backup_path
    return output_path


def print_summary(results):
    total = len(results)
    not_found_counts = {}
    vendor_counts = {}
    ocr_count = 0

    for r in results:
        vendor = r.get("Vendor", "UNKNOWN")
        vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1
        if r.get("_ocr_used"):
            ocr_count += 1
        for k, v in r.items():
            if v == "NOT FOUND" and not k.startswith("_"):
                not_found_counts[k] = not_found_counts.get(k, 0) + 1

    print(f"\n{'='*60}")
    print(f"PROCESSING SUMMARY")
    print(f"{'='*60}")
    print(f"Total files processed: {total}")
    print(f"Files that used OCR fallback: {ocr_count}")
    print(f"\nBy Vendor:")
    for vendor, count in sorted(vendor_counts.items()):
        print(f"  {vendor}: {count}")
    print(f"\n'NOT FOUND' fields:")
    for field, count in sorted(not_found_counts.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        print(f"  {field}: {count} ({pct:.0f}%)")
    print(f"{'='*60}\n")


# ============================================================================
# MAIN
# ============================================================================

def process_folder(folder_path):
    results = []
    failed = []

    folder_path = folder_path.rstrip("\\").rstrip("/")
    pattern = os.path.join(folder_path, "*.pdf")
    pdf_files = glob.glob(pattern)

    print(f"Found {len(pdf_files)} PDF files in {folder_path}")
    print("-" * 60)

    for pdf_path in sorted(pdf_files):
        filename = os.path.basename(pdf_path)
        try:
            result = process_pdf(pdf_path, use_ocr=False)
            results.append(result)
            print(f"  OK: {filename}")
        except Exception as e:
            print(f"  ERR: {filename} -> {e}")
            failed.append(make_empty_result(filename))

    all_results = results + failed
    output_path = os.path.join(folder_path, "extracted_invoice_data.xlsx")
    write_excel(all_results, output_path, folder_path)
    print_summary(all_results)

    print(f"Results saved to: {output_path}")
    return all_results


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = r"J:\67.235\Drive F\Data Tigard\Account Payable\WFH 2020\07 Stanley\AP - CM\0. OCR\File untuk diolah-Opencode"

    print(f"Processing folder: {folder}")
    process_folder(folder)
