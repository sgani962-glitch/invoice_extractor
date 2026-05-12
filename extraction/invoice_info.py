import re
from datetime import datetime


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
