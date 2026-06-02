import re
import hashlib
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from difflib import SequenceMatcher
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


# ---------------- UTIL ----------------

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


# ---------------- AI ENTITY SCORING ----------------

def entity_score(text):

    t = text.lower()
    score = 0

    # ORGANIZATION SIGNALS
    org_keywords = [
        "education", "university", "college", "institute",
        "consult", "international", "group", "agency"
    ]

    score += sum(1 for k in org_keywords if k in t)

    # CONTACT SIGNALS
    if "@" in t:
        score += 3

    if re.search(r"\+?\d[\d\s()-]{7,}\d", t):
        score += 2

    # COUNTRY SIGNALS
    countries = ["uk", "usa", "canada", "australia", "ireland", "new zealand"]
    score += sum(1 for c in countries if c in t)

    # STRUCTURE SIGNALS
    if len(text.split()) > 6:
        score += 1

    # NOISE PENALTY
    noise = [
        "click here", "return to", "home page",
        "if you", "read more", "navigation"
    ]

    if any(n in t for n in noise):
        score -= 5

    return score


# ---------------- AI NAME EXTRACTION ----------------

def extract_agent_name(text):

    words = text.split()

    # email-based hint
    emails = extract_emails(text)
    if emails:
        domain = emails[0].split("@")[-1]
        if "idp" in domain:
            return "IDP Education"
        if "si-uk" in domain:
            return "SI-UK Education Council"

    # capitalized phrase extraction
    candidates = []
    for i in range(len(words) - 2):
        chunk = " ".join(words[i:i+4])
        if chunk.istitle() or any(w[0].isupper() for w in chunk.split()):
            candidates.append(chunk)

    if candidates:
        return candidates[0][:60]

    return "Unknown Agent"


# ---------------- FETCH ----------------

def fetch_html(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=90000)
        page.wait_for_timeout(4000)
        html = page.content()
        browser.close()
        return html


# ---------------- EXTRACTION ----------------

def extract_blocks(soup):
    blocks = []

    for tag in soup.find_all(["tr", "li", "div", "p"]):
        txt = clean(tag.get_text(" "))
        if len(txt) > 30:
            blocks.append(txt)

    return blocks


def extract_entity(text, url):

    score = entity_score(text)

    if score < 4:
        return None  # AI FILTER

    return {
        "agent_name": extract_agent_name(text),
        "emails": extract_emails(text),
        "phones": extract_phones(text),
        "countries": [c for c in ["UK","USA","Canada","Australia"] if c.lower() in text.lower()],
        "notes": text[:200]
    }


# ---------------- CRM ----------------

class CRM:

    def __init__(self):
        self.master = {}
        self.map = {}

    def resolve(self, name):

        norm = name.lower().strip()

        for k in self.master:
            if similarity(norm, k) > 0.85:
                return k

        self.master[norm] = {
            "agent_id": generate_id(norm),
            "agent_name": name,
            "emails": set(),
            "phones": set(),
            "countries": set(),
            "count": 0
        }

        return norm

    def update(self, key, row):

        m = self.master[key]
        m["count"] += 1

        m["emails"].update(row.get("emails", []))
        m["phones"].update(row.get("phones", []))
        m["countries"].update(row.get("countries", []))

        self.map.setdefault(key, []).append(row)


# ---------------- SCRAPER ----------------

def scrape(url):

    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")

    blocks = extract_blocks(soup)

    results = []

    for b in blocks:

        e = extract_entity(b, url)

        if not e:
            continue

        results.append({
            "university": "University Partner Network",
            "country_page": url,
            "agent_name": e["agent_name"],
            "agency_group": "AI Extracted",
            "website": url,
            "emails": e["emails"],
            "phones": e["phones"],
            "countries_supported": e["countries"],
            "cities_supported": [],
            "services": SERVICES,
            "notes": e["notes"],
            "source_url": url,
            "last_updated": datetime.today().strftime("%Y-%m-%d")
        })

    return results


# ---------------- PIPELINE ----------------

def run():

    all_rows = []

    for url in URLS:
        print("Scraping:", url)
        try:
            all_rows.extend(scrape(url))
        except Exception as e:
            print("Error:", url, e)

    crm = CRM()

    for r in all_rows:
        key = crm.resolve(r["agent_name"])
        crm.update(key, r)

    return crm


# ---------------- EXPORT ----------------

def export(crm):

    master = []

    for k, v in crm.master.items():

        master.append({
            "agent_id": v["agent_id"],
            "agent_name": v["agent_name"],
            "emails": "; ".join(v["emails"]),
            "phones": "; ".join(v["phones"]),
            "countries_supported": "; ".join(v["countries"]),
            "occurrences": v["count"]
        })

    pd.DataFrame(master).to_csv("agents_master_v11.csv", index=False)

    print("Saved: agents_master_v11.csv")


# ---------------- MAIN ----------------

if __name__ == "__main__":
    crm = run()
    export(crm)