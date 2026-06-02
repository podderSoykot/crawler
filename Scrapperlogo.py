import re
import os
import hashlib
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse, urljoin
from playwright.sync_api import sync_playwright


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

LOGO_DIR = r"E:\Soykot\Scraping\crawler\logo"
os.makedirs(LOGO_DIR, exist_ok=True)

DOWNLOADED_LOGOS = {}

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


def generate_id(text):
    return hashlib.md5(text.encode()).hexdigest()[:12]


# =========================
# FETCH HTML
# =========================

def fetch_html(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=90000)
        page.wait_for_timeout(3500)
        html = page.content()
        browser.close()
        return html


# =========================
# SMART LOGO DETECTOR (FIXED)
# =========================

def extract_logo_url(soup, base_url):

    # 1. OpenGraph (highest priority)
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        return urljoin(base_url, og["content"])

    # 2. Twitter card
    tw = soup.find("meta", property="twitter:image")
    if tw and tw.get("content"):
        return urljoin(base_url, tw["content"])

    candidates = []

    # 3. DOM-based logo detection
    for img in soup.find_all("img"):

        src = (
            img.get("src")
            or img.get("data-src")
            or img.get("data-original")
            or img.get("data-lazy")
            or ""
        )

        if not src:
            continue

        alt = (img.get("alt") or "").lower()
        cls = " ".join(img.get("class", [])).lower()

        score = 0

        # strong signals for logos
        if "logo" in src.lower(): score += 6
        if "logo" in alt: score += 6
        if "logo" in cls: score += 6

        # avoid wrong images
        if "banner" in src.lower(): score -= 5
        if "hero" in src.lower(): score -= 5
        if "header" in src.lower(): score -= 2
        if "social" in src.lower(): score -= 3

        # file type preference
        if src.endswith(".svg"): score += 2
        if src.endswith(".png"): score += 1

        if score >= 6:
            candidates.append((score, urljoin(base_url, src)))

    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][1]

    return None


# =========================
# LOGO DOWNLOADER (CLEAN + SAFE)
# =========================

def download_logo(url, name):

    if not url:
        return ""

    if url in DOWNLOADED_LOGOS:
        return DOWNLOADED_LOGOS[url]

    try:
        filename = f"{generate_id(name)}.png"
        path = os.path.join(LOGO_DIR, filename)

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "image/*,*/*;q=0.8"
        }

        r = requests.get(url, headers=headers, timeout=20)

        print(f"[LOGO] {url} -> {r.status_code}")

        if r.status_code != 200:
            return ""

        if len(r.content) < 2000:
            return ""

        with open(path, "wb") as f:
            f.write(r.content)

        DOWNLOADED_LOGOS[url] = path
        return path

    except Exception as e:
        print("[ERROR] logo download:", e)

    return ""


# =========================
# UNIVERSITY DETECTION
# =========================

def infer_university(url, soup):

    domain = urlparse(url).netloc

    mapping = {
        "shu.ac.uk": "Sheffield Hallam University",
        "essex.ac.uk": "University of Essex",
        "gold.ac.uk": "Goldsmiths University of London",
        "hud.ac.uk": "University of Huddersfield",
        "beds.ac.uk": "University of Bedfordshire",
        "aru.ac.uk": "Anglia Ruskin University",
        "worcester.ac.uk": "University of Worcester",
        "lancashire.ac.uk": "University of Central Lancashire",
    }

    for k, v in mapping.items():
        if k in domain:
            return v

    return soup.title.string.strip() if soup.title else "Unknown University"


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
# AGENT NAME
# =========================

def extract_agent_name(text):

    emails = extract_emails(text)

    if emails:
        domain = emails[0].split("@")[-1]
        if "idp" in domain:
            return "IDP Education"
        if "si-uk" in domain:
            return "SI-UK Education Council"

    return "Unknown Agent"


# =========================
# SCRAPER
# =========================

def scrape(url):

    print("\nScraping:", url)

    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")

    university = infer_university(url, soup)
    blocks = extract_blocks(soup)

    logo_url = extract_logo_url(soup, url)
    print("LOGO FOUND:", logo_url)

    # IMPORTANT: download ONLY ONCE per page
    logo_path = download_logo(logo_url, university)

    results = []

    for b in blocks:

        results.append({
            "university": university,
            "website": url,
            "agent_name": extract_agent_name(b),
            "emails": extract_emails(b),

            "logo_url": logo_url,
            "logo_path": logo_path,

            "notes": b[:200],
            "last_updated": datetime.today().strftime("%Y-%m-%d")
        })

    return results


# =========================
# PIPELINE
# =========================

def run():

    all_data = []

    for url in URLS:
        try:
            all_data.extend(scrape(url))
        except Exception as e:
            print("Error:", url, e)

    df = pd.DataFrame(all_data)

    df.drop_duplicates(subset=["agent_name", "website"], inplace=True)

    return df


# =========================
# EXPORT
# =========================

def export(df):
    out = "agents_master_final_v4.csv"
    df.to_csv(out, index=False)
    print("\nSaved:", out)


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    df = run()
    export(df)