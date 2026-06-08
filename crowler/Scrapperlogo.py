import re
import os
import hashlib
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
from datetime import datetime

# =========================
# CONFIG
# =========================

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

LOGO_DIR = "logos"
os.makedirs(LOGO_DIR, exist_ok=True)

CACHE = {}
VISITED_AGENTS = {}

# =========================
# PLAYWRIGHT (SAFE INIT)
# =========================

playwright = sync_playwright().start()
browser = playwright.chromium.launch(headless=True)
context = browser.new_context()

# =========================
# FETCH PAGE
# =========================

def fetch(url):
    try:
        page = context.new_page()
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        html = page.content()
        page.close()
        return html
    except:
        return ""

# =========================
# UTIL
# =========================

def clean(t):
    return re.sub(r"\s+", " ", t or "").strip()


def hash_id(t):
    return hashlib.md5(t.encode()).hexdigest()[:10]


def extract_emails(text):
    return list(set(re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text or ""
    )))


def extract_phones(text):
    phones = re.findall(
        r"(?:\+\d{1,3}[\s\-]?)?(?:\(?\d+\)?[\s\-]?){6,}",
        text or ""
    )

    return list(set([
        p.strip()
        for p in phones
        if len(re.sub(r"\D", "", p)) >= 8
    ]))


# =========================
# LOGO EXTRACTION
# =========================

def extract_logo(soup, base_url):

    selectors = [
        ".logo img",
        "#logo img",
        ".navbar-brand img",
        ".site-logo img",
        "header img"
    ]

    for sel in selectors:
        try:
            img = soup.select_one(sel)
            if img:
                src = img.get("src") or img.get("data-src")
                if src:
                    return urljoin(base_url, src)
        except:
            pass

    return None


def download_logo(url, name):

    if not url:
        return ""

    if url in CACHE:
        return CACHE[url]

    try:
        r = requests.get(url, timeout=20)

        if r.status_code != 200:
            return ""

        ctype = r.headers.get("Content-Type", "").lower()

        ext = ".png"
        if "svg" in ctype:
            ext = ".svg"
        elif "jpg" in ctype or "jpeg" in ctype:
            ext = ".jpg"
        elif "webp" in ctype:
            ext = ".webp"

        path = os.path.join(LOGO_DIR, f"{hash_id(name)}{ext}")

        with open(path, "wb") as f:
            f.write(r.content)

        CACHE[url] = path
        return path

    except:
        return ""


# =========================
# STEP 1: UNIVERSITY → AGENTS
# =========================

def extract_agents(soup, base_url):

    agents = []

    for a in soup.find_all("a"):

        name = clean(a.get_text())
        href = a.get("href")

        if not href or len(name) < 3:
            continue

        full_url = urljoin(base_url, href)

        if any(x in full_url.lower() for x in [
            "mailto", "javascript", "#"
        ]):
            continue

        if name.lower() in ["home", "about", "contact", "menu"]:
            continue

        if not any(k in name.lower() for k in [
            "agent", "education", "consult", "study", "international"
        ]):
            continue

        agents.append({
            "agent_name": name,
            "agent_url": full_url
        })

    # dedupe
    seen = set()
    out = []

    for a in agents:
        key = (a["agent_name"], a["agent_url"])
        if key not in seen:
            seen.add(key)
            out.append(a)

    return out


# =========================
# STEP 2: AGENT WEBSITE SCRAPER
# =========================

def scrape_agent_site(url):

    if url in VISITED_AGENTS:
        return VISITED_AGENTS[url]

    try:
        html = fetch(url)

        if not html:
            return {"emails": [], "phones": [], "logo_url": None}

        soup = BeautifulSoup(html, "lxml")

        text = soup.get_text(" ", strip=True)

        data = {
            "emails": extract_emails(text),
            "phones": extract_phones(text),
            "logo_url": extract_logo(soup, url)
        }

        VISITED_AGENTS[url] = data
        return data

    except:
        return {"emails": [], "phones": [], "logo_url": None}


# =========================
# MAIN SCRAPER
# =========================

def scrape(url):

    print("\nScraping:", url)

    html = fetch(url)

    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")

    agents = extract_agents(soup, url)

    print("Agents found:", len(agents))

    results = []

    for a in agents:

        print("  -> Agent:", a["agent_name"])

        contact = scrape_agent_site(a["agent_url"])

        logo_path = download_logo(
            contact["logo_url"],
            a["agent_name"]
        )

        results.append({
            "agent_name": a["agent_name"],
            "agent_url": a["agent_url"],

            "emails": "; ".join(contact["emails"]),
            "phones": "; ".join(contact["phones"]),

            "logo_url": contact["logo_url"],
            "logo_path": logo_path,

            "source": url,
            "last_updated": datetime.today().strftime("%Y-%m-%d")
        })

    return results


# =========================
# RUN PIPELINE
# =========================

def run():

    all_data = []

    for url in URLS:
        print("\n========================")
        print("START:", url)

        try:
            all_data.extend(scrape(url))
        except Exception as e:
            print("FAILED:", url, e)

        print("DONE:", url)

    return pd.DataFrame(all_data)


# =========================
# EXPORT
# =========================

def export(df):

    df.drop_duplicates(
        subset=["agent_name", "agent_url"],
        inplace=True
    )

    df.to_csv("agents_final_v5.csv", index=False)

    print("\nSaved: agents_final_v5.csv")


# =========================
# CLEAN EXIT
# =========================

if __name__ == "__main__":

    try:
        df = run()
        export(df)

    finally:
        context.close()
        browser.close()
        playwright.stop()