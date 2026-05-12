import pdfplumber, re


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
            if re.search(r"^\s*Faktur\s+Pajak", next_text, re.MULTILINE):
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
