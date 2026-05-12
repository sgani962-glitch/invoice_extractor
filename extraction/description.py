import re


def extract_description(text):
    lines = text.strip().split(chr(10))

    header_pattern = re.compile(
        r'No\.\s*Barang\s*/\s*Nama\s*Barang\s*Kena\s*Pajak\s*/\s*Jasa\s*Kena\s*Pajak\s*Uang\s*Muka\s*/\s*Termin',
        re.IGNORECASE,
    )
    price_pattern = re.compile(r'Rp\s+[\d.,]+\s+x\s+[\d.,]+\s+(?:Bulan|Lainnya)', re.IGNORECASE)

    header_idx = None
    price_idx = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if header_pattern.search(stripped):
            header_idx = i
        elif price_pattern.search(stripped):
            price_idx = i

    if header_idx is None or price_idx is None:
        return 'NOT FOUND'

    if price_idx <= header_idx + 1:
        return 'NOT FOUND'

    between = lines[header_idx + 1 : price_idx]
    combined = ' '.join(l.strip() for l in between if l.strip())
    combined = re.sub(r'\s+', ' ', combined).strip()

    if len(combined) > 0:
        return combined
    return 'NOT FOUND'
