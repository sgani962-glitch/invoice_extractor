import re


def clean_text(text):
    text = text.replace("|", "I")
    text = text.replace("\r", " ")
    text = re.sub(r"[\x0c]", " ", text)
    text = re.sub(r"[^a-zA-Z0-9./:\-\s,()]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_spaces(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()
