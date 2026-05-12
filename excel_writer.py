import os
import pandas as pd
from config import OUTPUT_COLUMNS


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
