import re
import hashlib
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from difflib import SequenceMatcher
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright


URLS = [
    "https://international-agents.shu.ac.uk/",
    "https://www.essex.ac.uk/international/educational-representatives",
    "https://www.gold.ac.uk/international/representatives/list/",
    "https://www.hud.ac.uk/international/applying-to-the-university/approved-education-agents/",
    "https://www.beds.ac.uk/media/krmpi32p/overseas-agent-list_apr26.pdf",
    "https://www.aru.ac.uk/international/information-by-world-region",
    "https://www.worcester.ac.uk/study/International/local-representatives-near-you.aspx",
    "https://www.lancashire.ac.uk/international-students/country"
]

SERVICES = [
    "course_selection",
    "application_support",
    "visa_guidance",
    "counselling",
    "scholarship_guidance"
]

# =========================
# UTILITIES
# =========================

def clean(t):
    return re.sub(r"\s+", " ", (t or "")).strip()


def extract_emails(t):
    return list(set(re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", t or "")))


def extract_phones(t):
    return list(set(re.findall(r"\+?\d[\d\s()-]{7,}\d", t or "")))


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def generate_id(name):
    return hashlib.md5(name.encode()).hexdigest()[:12]


# =========================
# FETCH HTML
# =========================

def fetch_html(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=90000)
        page.wait_for_timeout(4000)
        html = page.content()
        browser.close()
        return html


# =========================
# AI SCORING
# =========================

def entity_score(text):

    t = text.lower()
    score = 0

    org_keywords = [
        "education", "university", "college",
        "institute", "consult", "international",
        "agency", "group"
    ]

    score += sum(1 for k in org_keywords if k in t)

    if "@" in t:
        score += 3

    if re.search(r"\+?\d[\d\s()-]{7,}\d", t):
        score += 2

    if len(text.split()) > 6:
        score += 1

    noise = [
        "click here", "return to", "home page",
        "if you", "read more", "navigation",
        "breadcrumb", "skip to content"
    ]

    if any(n in t for n in noise):
        score -= 5

    return score


# =========================
# AGENT NAME EXTRACTION
# =========================

def extract_agent_name(text):

    emails = extract_emails(text)

    if emails:
        domain = emails[0].split("@")[-1]
        if "idp" in domain:
            return "IDP Education"
        if "si-uk" in domain:
            return "SI-UK Education Council"

    words = text.split()
    candidates = []

    for i in range(len(words) - 2):
        chunk = " ".join(words[i:i+4])
        if chunk.istitle() or any(w[:1].isupper() for w in chunk.split()):
            candidates.append(chunk)

    if candidates:
        return candidates[0][:60]

    return "Unknown Agent"


# =========================
# UNIVERSITY + COUNTRY
# =========================

def infer_university_and_country(soup, url):

    text = soup.get_text(" ").lower()
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    domain = urlparse(url).netloc

    university = title if title else "Unknown University"

    if "shu.ac.uk" in domain:
        university = "Sheffield Hallam University"
    elif "essex.ac.uk" in domain:
        university = "University of Essex"
    elif "gold.ac.uk" in domain:
        university = "Goldsmiths University of London"
    elif "hud.ac.uk" in domain:
        university = "University of Huddersfield"
    elif "beds.ac.uk" in domain:
        university = "University of Bedfordshire"
    elif "aru.ac.uk" in domain:
        university = "Anglia Ruskin University"
    elif "worcester.ac.uk" in domain:
        university = "University of Worcester"
    elif "lancashire.ac.uk" in domain:
        university = "University of Central Lancashire"

    country = "Unknown"

    if any(k in text for k in ["uk", "london", "england", "scotland"]):
        country = "United Kingdom"
    elif any(k in text for k in ["usa", "united states"]):
        country = "USA"
    elif "canada" in text:
        country = "Canada"
    elif "australia" in text:
        country = "Australia"
    elif ".uk" in domain:
        country = "United Kingdom"

    return university, country


# =========================
# BLOCK EXTRACTION
# =========================

def extract_blocks(soup):
    blocks = []
    for tag in soup.find_all(["tr", "li", "div", "p"]):
        txt = clean(tag.get_text(" "))
        if len(txt) > 30:
            blocks.append(txt)
    return blocks


# =========================
# ENTITY FILTER
# =========================

def extract_entity(text):

    score = entity_score(text)

    if score < 4:
        return None

    return {
        "agent_name": extract_agent_name(text),
        "emails": extract_emails(text),
        "phones": extract_phones(text),
        "countries": []
    }


# =========================
# SCRAPER
# =========================

def scrape(url):

    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")

    blocks = extract_blocks(soup)

    university, country = infer_university_and_country(soup, url)

    results = []

    for b in blocks:

        e = extract_entity(b)

        if not e:
            continue

        results.append({
            "university": university,
            "country_name": country,
            "country_page": url,
            "agent_name": e["agent_name"],
            "agency_group": "AI Extracted",
            "website": url,
            "emails": e["emails"],
            "phones": e["phones"],
            "countries_supported": e["countries"],
            "cities_supported": [],
            "services": SERVICES,
            "notes": b[:200],
            "source_url": url,
            "last_updated": datetime.today().strftime("%Y-%m-%d")
        })

    return results


# =========================
# PIPELINE
# =========================

def run():

    all_rows = []

    for url in URLS:
        print("Scraping:", url)
        try:
            all_rows.extend(scrape(url))
        except Exception as e:
            print("Error:", url, e)

    return pd.DataFrame(all_rows)


# =========================
# EXPORT (CSV ONLY)
# =========================

def export(df):

    df.to_csv("agents_master_v12.csv", index=False)

    print("Saved: agents_master_v12.csv")


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    df = run()
    export(df)