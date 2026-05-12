import re


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


def format_invoice_number(text):
    if not text:
        return "NOT FOUND"
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text
