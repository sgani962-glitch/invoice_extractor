import os
import sys


def get_tesseract_lang():
    return "ind"


def preprocess_image(img_bytes):
    import numpy as np
    import cv2
    from PIL import Image
    import io

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
    from processors.pdf_scanner import render_page_to_image
    img_bytes = render_page_to_image(pdf_path, page_num)
    text = ocr_image(img_bytes)
    return text
