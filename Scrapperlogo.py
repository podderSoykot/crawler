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
]

LOGO_DIR = "logos"
os.makedirs(LOGO_DIR, exist_ok=True)

CACHE = {}
VISITED_AGENTS = {}

# =========================
# FETCH (FIXED - NO HANG)
# =========================

def fetch(url):

    browser = None

    try:
        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )

            page = browser.new_page()

            page.set_default_navigation_timeout(30000)
            page.set_default_timeout(30000)

            print(f"   Loading page...")

            page.goto(url, wait_until="domcontentloaded")

            page.wait_for_timeout(2000)

            html = page.content()

            return html

    except Exception as e:
        print(f"[FETCH ERROR] {url} -> {e}")
        return ""

    finally:
        if browser:
            browser.close()


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
# LOGO EXTRACT
# =========================

def extract_site_logo(soup, base_url):

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


# =========================
# DOWNLOAD LOGO
# =========================

def download_logo(url, name):

    if not url:
        return ""

    if url in CACHE:
        return CACHE[url]

    try:
        r = requests.get(url, timeout=20)

        if r.status_code != 200:
            return ""

        ext = ".png"

        ctype = r.headers.get("Content-Type", "").lower()

        if "svg" in ctype:
            ext = ".svg"
        elif "jpeg" in ctype or "jpg" in ctype:
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
# AGENT EXTRACTION
# =========================

def extract_agents(soup, base_url):

    agents = []

    for a in soup.find_all("a"):

        name = clean(a.get_text())
        href = a.get("href")

        if not href or len(name) < 3 or len(name) > 100:
            continue

        full_url = urljoin(base_url, href)

        if any(x in full_url.lower() for x in [
            "mailto", "javascript", "#", "login", "contact"
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

    # remove duplicates
    seen = set()
    out = []

    for a in agents:
        key = (a["agent_name"], a["agent_url"])
        if key not in seen:
            seen.add(key)
            out.append(a)

    return out


# =========================
# AGENT WEBSITE SCRAPE
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

        emails = extract_emails(text)
        phones = extract_phones(text)

        logo_url = extract_site_logo(soup, url)

        data = {
            "emails": emails,
            "phones": phones,
            "logo_url": logo_url
        }

        VISITED_AGENTS[url] = data

        return data

    except:
        return {"emails": [], "phones": [], "logo_url": None}


# =========================
# SCRAPE UNIVERSITY
# =========================

def scrape(url):

    print("\nScraping:", url)

    html = fetch(url)

    if not html:
        print("   EMPTY PAGE SKIPPED")
        return []

    soup = BeautifulSoup(html, "lxml")

    agents = extract_agents(soup, url)

    print(f"   Agents found: {len(agents)}")

    results = []

    for a in agents:

        print("   Agent:", a["agent_name"])

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
# RUN
# =========================

def run():

    all_data = []

    for url in URLS:
        print("\n========================")
        print("START:", url)

        try:
            data = scrape(url)
            all_data.extend(data)
        except Exception as e:
            print("FAILED:", url, e)

        print("DONE:", url)

    df = pd.DataFrame(all_data)

    df.drop_duplicates(subset=["agent_name", "agent_url"], inplace=True)

    return df


# =========================
# EXPORT
# =========================

def export(df):
    out = "agents_final_fixed.csv"
    df.to_csv(out, index=False)
    print("\nSaved:", out)


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    df = run()
    export(df)