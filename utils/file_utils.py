import re
from config import FILENAME_VENDOR_PATTERNS


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
