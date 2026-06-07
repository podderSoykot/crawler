import re
from bs4 import BeautifulSoup

bn_to_en = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def remove_html(text):
    return BeautifulSoup(str(text), "html.parser").get_text()

def clean_noise(text):
    text = str(text)

    text = re.sub(r"\b\d{5,}\b", " ", text)   # large numbers
    text = re.sub(r"\b\d+\.\d+\b", " ", text) # decimals

    return text

def extract_year(text):

    text_lower = text.lower()

    # ❌ ignore finance/math questions
    math_keywords = [
        "interest", "tk", "taka", "rate", "annual", "compounded",
        "earn", "loan", "money", "percent", "principal", "installment"
    ]

    if any(word in text_lower for word in math_keywords):
        return None

    match = re.search(r"\b(19\d{2}|20\d{2})\b", text)

    if match:
        return match.group(1)

    return None


def clean_question(q):

    if q is None:
        return None

    q = str(q)
    q = remove_html(q)
    q = re.sub(r"\s+", " ", q).strip()


    q_norm = q.translate(bn_to_en)
    q_norm = clean_noise(q_norm)

    year = extract_year(q_norm)

    return {
        "question": q,
        "clean_question": q_norm,
        "year": year
    }