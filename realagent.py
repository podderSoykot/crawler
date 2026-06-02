import re
import os
import hashlib
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from playwright.sync_api import sync_playwright

# =========================
# CONFIG
# =========================

URLS = [
    "https://international-agents.shu.ac.uk/",
    "https://www.essex.ac.uk/international/educational-representatives",
    "https://www.gold.ac.uk/international/representatives/list/",
    "https://www.hud.ac.uk/international/applying-to-the-university/approved-education-agents/",
]

LOGO_DIR = "logos"
os.makedirs(LOGO_DIR, exist_ok=True)

CACHE = {}
VISITED = {}

# =========================
# PLAYWRIGHT INIT (STABLE)
# =========================

playwright = sync_playwright().start()
browser = playwright.chromium.launch(headless=True)
context = browser.new_context()

# =========================
# FETCH
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


def is_noise(name):
    bad = [
        "study", "international", "home", "about", "contact",
        "menu", "apply", "login", "search", "university",
        "information", "overview", "page"
    ]
    return any(b in name.lower() for b in bad)


# =========================
# COUNTRY DETECTION
# =========================

COUNTRIES = [
    "bangladesh","india","pakistan","nepal","sri lanka","china",
    "usa","uk","canada","australia","uae","malaysia","saudi"
]

def extract_countries(text):
    text = (text or "").lower()
    return list(set([c.title() for c in COUNTRIES if c in text]))


# =========================
# SMART AGENT DETECTION ENGINE
# =========================

def extract_agents(soup, base_url):

    agents = []

    # =========================
    # LAYER 1: TABLES (HIGH VALUE)
    # =========================
    for row in soup.find_all("tr"):
        text = clean(row.get_text(" "))
        links = row.find_all("a")

        for a in links:
            name = clean(a.get_text())
            href = a.get("href")

            if not href or len(name) < 3:
                continue

            if is_noise(name):
                continue

            full_url = urljoin(base_url, href)

            agents.append({
                "name": name,
                "url": full_url,
                "context": text
            })

    # =========================
    # LAYER 2: LISTS
    # =========================
    for li in soup.find_all("li"):
        text = clean(li.get_text(" "))
        links = li.find_all("a")

        for a in links:
            name = clean(a.get_text())
            href = a.get("href")

            if not href or len(name) < 3:
                continue

            if is_noise(name):
                continue

            full_url = urljoin(base_url, href)

            agents.append({
                "name": name,
                "url": full_url,
                "context": text
            })

    # =========================
    # LAYER 3: DIV BLOCKS (fallback)
    # =========================
    for div in soup.find_all("div"):
        text = clean(div.get_text(" "))

        if "agent" not in text.lower():
            continue

        links = div.find_all("a")

        for a in links:
            name = clean(a.get_text())
            href = a.get("href")

            if not href or is_noise(name):
                continue

            full_url = urljoin(base_url, href)

            agents.append({
                "name": name,
                "url": full_url,
                "context": text
            })

    # =========================
    # CLEAN + FILTER
    # =========================
    seen = set()
    out = []

    for a in agents:
        key = (a["name"], a["url"])
        if key in seen:
            continue
        seen.add(key)

        if len(a["name"]) < 3 or len(a["name"]) > 120:
            continue

        out.append(a)

    return out


# =========================
# AGENT SITE SCRAPER
# =========================

def scrape_agent_site(url):

    if url in VISITED:
        return VISITED[url]

    try:
        html = fetch(url)

        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(" ", strip=True)

        emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)

        phones = re.findall(r"(?:\+\d{1,3}[\s\-]?)?(?:\(?\d+\)?[\s\-]?){6,}", text)

        countries = extract_countries(text)

        data = {
            "emails": list(set(emails)),
            "phones": list(set(phones)),
            "countries": countries
        }

        VISITED[url] = data
        return data

    except:
        return {"emails": [], "phones": [], "countries": []}


# =========================
# SCRAPE PIPELINE
# =========================

def scrape(url):

    print("\nScraping:", url)

    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")

    agents = extract_agents(soup, url)

    print("Agents found:", len(agents))

    results = []

    for a in agents:

        contact = scrape_agent_site(a["url"])

        results.append({
            "agent_name": a["name"],
            "agent_url": a["url"],
            "emails": "; ".join(contact["emails"]),
            "phones": "; ".join(contact["phones"]),
            "countries": ", ".join(contact["countries"]),
            "source": url,
            "last_updated": datetime.today().strftime("%Y-%m-%d")
        })

    return results


# =========================
# RUN
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
    df.drop_duplicates(subset=["agent_name", "agent_url"], inplace=True)
    df.to_csv("agents_v7_perfect.csv", index=False)
    print("\nSaved: agents_v7_perfect.csv")


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