import pandas as pd
import re

# =========================
# FILES
# =========================


INPUT_FILE = "agents_final_v5.csv"
OUTPUT_FILE = "agents_final_clean.csv"

# =========================
# NOISE FILTERS
# =========================

BAD_KEYWORDS = [
    "study", "course", "undergraduate", "postgraduate",
    "international student support", "home", "about",
    "apply", "blog", "news", "event", "life",
    "contact", "information", "services", "support",
    "login", "search", "menu", "university", "page",
    "overview", "admissions", "programme", "program",
    "study abroad", "student support"
]

BAD_URL_PARTS = ["javascript", "mailto:", "#", "tel:"]

# =========================
# CLEAN FUNCTIONS
# =========================

def clean_text(t):
    t = str(t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()

def is_noise(name):
    name = str(name).lower()
    return any(k in name for k in BAD_KEYWORDS)

def is_bad_url(url):
    url = str(url).lower()
    return any(b in url for b in BAD_URL_PARTS)

def extract_domain(url):
    try:
        return url.split("/")[2]
    except:
        return ""

# =========================
# MAIN CLEANER
# =========================

def clean_df(df):

    print("Starting full cleaning...")

    # drop empty
    df = df.dropna(subset=["agent_name", "agent_url"])

    # clean text
    df["agent_name"] = df["agent_name"].apply(clean_text)
    df["agent_url"] = df["agent_url"].apply(clean_text)

    # remove noise
    df = df[~df["agent_name"].apply(is_noise)]
    df = df[~df["agent_url"].apply(is_bad_url)]

    # remove very short / invalid names
    df = df[df["agent_name"].str.len() >= 3]
    df = df[df["agent_name"].str.len() <= 120]

    # clean emails/phones if exist
    if "emails" in df.columns:
        df["emails"] = df["emails"].fillna("").apply(clean_text)

    if "phones" in df.columns:
        df["phones"] = df["phones"].fillna("").apply(clean_text)

    # add domain
    df["domain"] = df["agent_url"].apply(extract_domain)

    # deduplicate
    df = df.drop_duplicates(subset=["agent_name", "agent_url"])

    # reset index
    df = df.reset_index(drop=True)

    print(f"Final cleaned rows: {len(df)}")

    return df

# =========================
# RUN PIPELINE
# =========================

def run():

    print(f"Loading raw file: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE)

    df_clean = clean_df(df)

    # FINAL SINGLE OUTPUT CSV
    df_clean.to_csv(OUTPUT_FILE, index=False)

    print(f"\nSaved FINAL CLEAN CSV: {OUTPUT_FILE}")

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    run()