import os
from extraction.invoice_info import extract_invoice_no, extract_invoice_date
from extraction.tax_info import extract_tax_invoice_no, extract_dpp, extract_ppn, extract_vendor_name, extract_vendor_npwp, extract_buyer_npwp
from extraction.description import extract_description
from processors.pdf_scanner import find_faktur_pajak_page, extract_fp_text, render_page_to_image
from utils.clean_text import clean_text
from utils.file_utils import detect_vendor_from_filename, extract_invoice_no_from_filename
from utils.text_utils import format_currency
from config import VENDOR_MAP, VENDOR_PO_MAP


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


def process_pdf(pdf_path, use_ocr=True):
    filename = os.path.basename(pdf_path)
    fp_text = extract_fp_text(pdf_path)

    if not fp_text:
        return make_empty_result(filename)

    result = extract_all_fields(fp_text, filename, use_ocr_fallback=False)

    if use_ocr and result_is_poor(result):
        from processors.ocr_processor import ocr_pdf_page
        page_num, _ = find_faktur_pajak_page(pdf_path)
        if page_num is not None:
            ocr_text = ocr_pdf_page(pdf_path, page_num)
            if ocr_text:
                result_ocr = extract_all_fields(ocr_text, filename, use_ocr_fallback=True)
                if count_valid_fields(result_ocr) > count_valid_fields(result):
                    result = result_ocr

    return result


def result_is_poor(result):
    not_found_count = sum(1 for k, v in result.items() if v == "NOT FOUND" and k not in ["Due Date", "_vendor_npwp", "_buyer_npwp", "_ocr_used"])
    return not_found_count >= 3


def count_valid_fields(result):
    return sum(1 for k, v in result.items() if v not in ["NOT FOUND", "", "0,00"] and not k.startswith("_"))


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
