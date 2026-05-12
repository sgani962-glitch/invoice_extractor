import os
import sys
import glob

sys.path.insert(0, os.path.dirname(__file__))

from processors.main_processor import process_pdf, make_empty_result
from excel_writer import write_excel, print_summary


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
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = r"J:\67.235\Drive F\Data Tigard\Account Payable\WFH 2020\07 Stanley\AP - CM\0. OCR\File untuk diolah-Opencode"

    print(f"Processing folder: {folder}")
    process_folder(folder)
