import re
from utils.text_utils import clean_number, format_currency


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
