"""
scrape_v25.py  ─  Office Intelligence Scraper with Live Progress
================================================================
Zero heavy dependencies — no spaCy, no nest_asyncio required.

SETUP (run once in your venv):
    pip install playwright pandas beautifulsoup4 requests
    playwright install chromium

RUN:
    python scrape_v25.py               # all 242 agents
    python scrape_v25.py --test 5      # first 5 only
    python scrape_v25.py --input my_agents.csv --output results.csv
"""

import asyncio
import re
import os
import sys
import time
import argparse
import requests
import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# ── nest_asyncio only needed inside Jupyter/Colab ─────────────────
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass  # not needed when running as a normal script on Windows/Mac/Linux


# ══════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════
INPUT_CSV  = "unique_agents_242.csv"
OUTPUT_CSV = "office_intelligence_v25.csv"
LOG_CSV    = "scrape_log_v25.csv"

RESUME     = True   # skip agents already in OUTPUT_CSV
PAGE_LIMIT = 6      # max pages scraped per agent

FALLBACK_PATHS = [
    "/contact", "/contact-us", "/offices", "/locations",
    "/about/contact", "/our-offices", "/en/contact",
    "/find-us", "/get-in-touch", "/global-offices",
]

# ── Regex ──────────────────────────────────────────────────────────
EMAIL_RE = re.compile(r"[\w\.\-\+]+@[\w\.\-]+\.\w{2,}", re.I)
PHONE_RE = re.compile(r"(\+?[\d][\d\s\-\(\)\.]{5,17}[\d])")

# ── Country list for regex-based GPE detection ─────────────────────
_COUNTRIES = [
    "Afghanistan","Albania","Algeria","Angola","Argentina","Armenia","Australia",
    "Austria","Azerbaijan","Bahrain","Bangladesh","Belarus","Belgium","Bolivia",
    "Bosnia","Botswana","Brazil","Bulgaria","Cambodia","Cameroon","Canada","Chile",
    "China","Colombia","Croatia","Cyprus","Czech Republic","Denmark","Ecuador",
    "Egypt","Estonia","Ethiopia","Finland","France","Georgia","Germany","Ghana",
    "Greece","Guatemala","Honduras","Hong Kong","Hungary","India","Indonesia",
    "Iran","Iraq","Ireland","Israel","Italy","Japan","Jordan","Kazakhstan","Kenya",
    "Kosovo","Kuwait","Kyrgyzstan","Latvia","Lebanon","Libya","Lithuania",
    "Luxembourg","Macau","Macao","Malaysia","Malta","Mauritius","Mexico",
    "Mongolia","Morocco","Myanmar","Nepal","Netherlands","New Zealand","Nigeria",
    "Norway","Oman","Pakistan","Palestine","Panama","Paraguay","Peru","Philippines",
    "Poland","Portugal","Qatar","Romania","Russia","Saudi Arabia","Senegal",
    "Serbia","Singapore","Slovakia","Slovenia","South Africa","South Korea",
    "Spain","Sri Lanka","Sudan","Sweden","Switzerland","Taiwan","Tajikistan",
    "Tanzania","Thailand","Tunisia","Turkey","Turkiye","Turkmenistan","Uganda",
    "Ukraine","United Arab Emirates","UAE","United Kingdom","UK",
    "United States","USA","Uruguay","Uzbekistan","Venezuela","Vietnam",
    "Yemen","Zambia","Zimbabwe",
]
# Sort longest first so "Saudi Arabia" matches before "Arabia"
_COUNTRIES_SORTED = sorted(_COUNTRIES, key=len, reverse=True)
COUNTRY_RE = re.compile(
    r"\b(" + "|".join(re.escape(c) for c in _COUNTRIES_SORTED) + r")\b",
    re.IGNORECASE,
)

# Common city indicators
CITY_RE = re.compile(
    r"\b(London|New York|Sydney|Melbourne|Toronto|Dubai|Singapore|Mumbai|"
    r"Delhi|New Delhi|Bangalore|Bengaluru|Chennai|Kolkata|Hyderabad|Karachi|"
    r"Lahore|Dhaka|Nairobi|Lagos|Accra|Cairo|Beirut|Amman|Riyadh|Jeddah|"
    r"Doha|Abu Dhabi|Kuala Lumpur|Jakarta|Manila|Bangkok|Ho Chi Minh|Hanoi|"
    r"Beijing|Shanghai|Guangzhou|Shenzhen|Hong Kong|Kowloon|Tokyo|Seoul|"
    r"Istanbul|Ankara|Paris|Berlin|Madrid|Rome|Amsterdam|Brussels|Vienna|"
    r"Warsaw|Prague|Budapest|Bucharest|Kiev|Kyiv|Moscow|Tashkent|Almaty|"
    r"Baku|Tbilisi|Yerevan|Colombo|Kathmandu|Islamabad|Kabul|Tehran|Baghdad|"
    r"Accra|Abuja|Dar es Salaam|Kampala|Addis Ababa|Casablanca|Tunis|Algiers|"
    r"Gurgaon|Noida|Pune|Ahmedabad|Chandigarh|Lucknow|Jaipur|Kochi|Goa)\b",
    re.IGNORECASE,
)


def detect_country_city(text):
    """Extract country and city from text using regex (no spaCy needed)."""
    cm = COUNTRY_RE.search(text)
    country = cm.group(1) if cm else None

    km = CITY_RE.search(text)
    city = km.group(1) if km else None

    return country, city


# ══════════════════════════════════════════════════════════════════
# ANSI COLOUR (works on Windows Terminal, Mac, Linux)
# ══════════════════════════════════════════════════════════════════
def _enable_win_ansi():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleMode(
                ctypes.windll.kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False
    return sys.stdout.isatty()

_COLOR = _enable_win_ansi()

def _c(code, s): return f"\033[{code}m{s}\033[0m" if _COLOR else s
def green(s):    return _c("32", s)
def red(s):      return _c("31", s)
def yellow(s):   return _c("33", s)
def cyan(s):     return _c("36", s)
def bold(s):     return _c("1",  s)
def dim(s):      return _c("2",  s)


# ══════════════════════════════════════════════════════════════════
# LIVE PROGRESS TABLE
# ══════════════════════════════════════════════════════════════════
class Progress:
    BAR_W   = 22
    COL_AG  = 30
    COL_URL = 26
    SEP     = "─" * 72

    def __init__(self, total: int):
        self.total   = total
        self.done    = 0
        self.rows    = []
        self.t0      = time.time()
        self._lines  = 0

    def start_agent(self, no, agent, url):
        self.rows.append({"no": no, "agent": agent,
                          "url": url, "found": None, "ok": None})
        self._render()

    def finish_agent(self, no, found, ok):
        for r in self.rows:
            if r["no"] == no:
                r["found"] = found
                r["ok"]    = ok
        self.done += 1
        self._render()

    def close(self):
        self._render(final=True)
        print()

    # ── internals ─────────────────────────────────────────────────
    def _bar(self):
        pct  = self.done / max(self.total, 1)
        fill = int(self.BAR_W * pct)
        return f"[{'█'*fill}{'░'*(self.BAR_W-fill)}] {pct*100:4.0f}%"

    def _eta(self):
        elapsed = time.time() - self.t0
        if self.done == 0:
            return "ETA: calculating..."
        left = (self.total - self.done) / (self.done / elapsed)
        return f"ETA ~{int(left//60)}m {int(left%60):02d}s"

    def _fmt(self, r):
        icon = yellow("↻") if r["ok"] is None else (green("✓") if r["ok"] else red("✗"))
        found_s = (yellow("   ...") if r["found"] is None
                   else (green(f"{r['found']:>6}") if r["found"] > 0
                         else dim(f"{r['found']:>6}")))
        return (f"  {icon}  {r['no']:>4}  "
                f"{r['agent'][:self.COL_AG]:<{self.COL_AG}}  "
                f"{r['url'][:self.COL_URL]:<{self.COL_URL}}  "
                f"{found_s}")

    def _render(self, final=False):
        lines = [
            dim(self.SEP),
            bold(f"  Processing  {self.done}/{self.total}  "
                 f"{self._bar()}   {self._eta()}"),
            dim(self.SEP),
            dim(f"  {'':2}  {'#':>4}  "
                f"{'Agent':<{self.COL_AG}}  "
                f"{'URL':<{self.COL_URL}}  "
                f"{'Found':>6}"),
            dim("─" * 72),
        ] + [self._fmt(r) for r in self.rows[-20:]] + [dim(self.SEP)]

        if self._lines:
            sys.stdout.write(f"\033[{self._lines}A\033[J")
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()
        self._lines = 0 if final else len(lines) + 1


# ══════════════════════════════════════════════════════════════════
# FAILURE DETECTION & HEALING
# ══════════════════════════════════════════════════════════════════
def classify_failure(html, status):
    if status in (401, 403):                 return "BOT_BLOCK"
    if status >= 500:                        return "NETWORK_FAIL"
    if html and len(html) < 500:             return "EMPTY_PAGE"
    if "redirect" in (html or "").lower():   return "REDIRECT_LOOP"
    return None


async def safe_load(page, url):
    try:
        resp   = await page.goto(url, timeout=20000, wait_until="domcontentloaded")
        status = resp.status if resp else 200
        html   = await page.content()
        return html, status, classify_failure(html, status)
    except Exception:
        return None, 0, "NETWORK_FAIL"


def fallback_http(url):
    try:
        r = requests.get(url, timeout=10,
                         headers={"User-Agent": "Mozilla/5.0"})
        return r.text if r.status_code == 200 else None
    except Exception:
        return None


async def heal(page, base_url, failure):
    if failure == "BOT_BLOCK":
        return fallback_http(base_url)
    if failure == "REDIRECT_LOOP":
        for path in FALLBACK_PATHS:
            html, _, f = await safe_load(page, base_url.rstrip("/") + path)
            if html and not f:
                return html
    if failure == "EMPTY_PAGE":
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)
        return await page.content()
    if failure == "NETWORK_FAIL":
        await asyncio.sleep(2)
        html, _, _ = await safe_load(page, base_url)
        return html
    return None


# ══════════════════════════════════════════════════════════════════
# EXTRACTION
# ══════════════════════════════════════════════════════════════════
def extract_blocks(html):
    soup = BeautifulSoup(html, "html.parser")
    out  = []
    for tag in soup.find_all(["div","section","li","article","p"]):
        text = tag.get_text(" ", strip=True)
        if len(text) >= 30 and (EMAIL_RE.search(text) or PHONE_RE.search(text)):
            out.append(text)
    return out


def parse_block(text, agent, url):
    country, city = detect_country_city(text)
    phones = "; ".join(dict.fromkeys(PHONE_RE.findall(text)))
    emails = "; ".join(dict.fromkeys(EMAIL_RE.findall(text)))
    return {
        "agent_name":  agent,
        "source_page": url,
        "country":     country,
        "city":        city,
        "emails":      emails or None,
        "phones":      phones or None,
    }


# ══════════════════════════════════════════════════════════════════
# AGENT PROCESSOR
# ══════════════════════════════════════════════════════════════════
async def process_agent(browser, agent, website):
    page    = await browser.new_page()
    results = []

    # Block images/fonts to speed up loading
    await page.route(
        re.compile(r"\.(png|jpg|jpeg|gif|webp|svg|woff2?|ttf|otf|mp4|mp3)(\?.*)?$", re.I),
        lambda route: route.abort(),
    )

    try:
        if not website.startswith("http"):
            website = "https://" + website

        html, status, failure = await safe_load(page, website)
        if failure:
            html = await heal(page, website, failure)
        if not html:
            return []

        # Discover contact links from homepage nav
        try:
            links = await page.eval_on_selector_all("a", "els => els.map(e => e.href)")
        except Exception:
            links = []

        contact_links = [
            l for l in links
            if l and any(k in l.lower()
                         for k in ["contact","office","location","branch","find-us"])
        ]

        pages_to_try = [website] + contact_links[: PAGE_LIMIT - 1]
        for path in FALLBACK_PATHS:
            c = website.rstrip("/") + path
            if c not in pages_to_try:
                pages_to_try.append(c)
        pages_to_try = pages_to_try[:PAGE_LIMIT]

        seen = set()
        for url in pages_to_try:
            if url in seen:
                continue
            seen.add(url)

            pg_html, _, pg_fail = await safe_load(page, url)
            if pg_fail:
                pg_html = await heal(page, url, pg_fail)
            if not pg_html:
                continue

            for block in extract_blocks(pg_html):
                results.append(parse_block(block, agent, url))

    except Exception:
        pass
    finally:
        await page.close()

    # Keep only rows that have email or phone
    return [r for r in results if r["emails"] or r["phones"]]


# ══════════════════════════════════════════════════════════════════
# SAVE
# ══════════════════════════════════════════════════════════════════
def _save(all_rows, log_rows):
    if all_rows:
        pd.DataFrame(all_rows).to_csv(OUTPUT_CSV, index=False)
    if log_rows:
        pd.DataFrame(log_rows).to_csv(LOG_CSV, index=False)


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════
async def main(test_n=None):
    df = pd.read_csv(INPUT_CSV)[["agent_name", "website"]].dropna()
    if test_n:
        df = df.head(test_n)

    # Resume
    done_names    = set()
    existing_rows = []
    if RESUME and os.path.exists(OUTPUT_CSV):
        old           = pd.read_csv(OUTPUT_CSV)
        done_names    = set(old["agent_name"].tolist())
        existing_rows = old.to_dict("records")

    pending = df[~df["agent_name"].isin(done_names)].reset_index(drop=True)

    print(f"\n{dim('─'*72)}")
    print(bold("  Office Intelligence Scraper  v25"))
    print(f"  Input          : {INPUT_CSV}")
    print(f"  Output         : {OUTPUT_CSV}")
    print(f"  Total agents   : {len(df)}")
    print(f"  Already done   : {len(done_names)}")
    print(f"  To process now : {len(pending)}")
    print(dim("─" * 72) + "\n")

    if pending.empty:
        print(green("✓ All agents already scraped. Nothing to do."))
        return

    prog      = Progress(total=len(pending))
    all_rows  = list(existing_rows)
    log_rows  = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )

        for idx, row in pending.iterrows():
            agent   = str(row["agent_name"]).strip()
            website = str(row["website"]).strip()
            no      = idx + 1

            display_url = (website
                           .replace("https://", "")
                           .replace("http://", "")
                           .rstrip("/"))

            prog.start_agent(no, agent, display_url)

            rows  = await process_agent(browser, agent, website)
            found = len(rows)
            all_rows.extend(rows)

            log_rows.append({
                "no":         no,
                "agent_name": agent,
                "url":        website,
                "found":      found,
                "status":     "success" if found > 0 else "no_data",
            })

            prog.finish_agent(no, found, ok=(found > 0))

            if no % 10 == 0:
                _save(all_rows, log_rows)

        await browser.close()

    prog.close()
    _save(all_rows, log_rows)

    log_df   = pd.DataFrame(log_rows)
    ok       = (log_df["status"] == "success").sum()
    total_of = int(log_df["found"].sum())

    print(bold("  COMPLETE"))
    print(f"  Agents processed  : {len(log_rows)}")
    print(f"  With data         : {green(str(ok))}")
    print(f"  No data           : {red(str(len(log_rows)-ok))}")
    print(f"  Sub-offices total : {bold(str(total_of))}")
    print(f"  Output            : {OUTPUT_CSV}")
    print(dim("─" * 72))

    if ok > 0:
        print(bold("\n  Top agents by sub-offices found:"))
        for _, r in log_df.nlargest(10, "found").iterrows():
            bar = cyan("█" * min(int(r["found"]), 35))
            print(f"    {int(r['no']):>3}.  "
                  f"{str(r['agent_name'])[:33]:<33}  "
                  f"{bar}  {bold(str(int(r['found'])))}")
    print()


# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Office Intelligence Scraper v25")
    parser.add_argument("--test",   type=int, default=None,
                        help="Process only the first N agents (for testing)")
    parser.add_argument("--input",  default=INPUT_CSV,
                        help=f"Input CSV (default: {INPUT_CSV})")
    parser.add_argument("--output", default=OUTPUT_CSV,
                        help=f"Output CSV (default: {OUTPUT_CSV})")
    args = parser.parse_args()

    INPUT_CSV  = args.input
    OUTPUT_CSV = args.output

    asyncio.run(main(test_n=args.test))