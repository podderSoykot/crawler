import os
import re
import time
import urllib.parse
from playwright.sync_api import sync_playwright
import pandas as pd

# -----------------------------
# PATH CONFIGURATION
# -----------------------------
INPUT_CSV = r"E:\Soykot\Scraping\crawler\data\goldsmiths_final_output.csv"
OUTPUT_CSV = r"E:\Soykot\Scraping\crawler\collect_CSV\essex_agents_scraped.csv"

# -----------------------------
# LOAD & RESUME DATA LOGIC
# -----------------------------
if not os.path.exists(INPUT_CSV):
    raise FileNotFoundError(f"Source file not found at: {INPUT_CSV}")

df_all = pd.read_csv(INPUT_CSV)
df_all.rename(columns={"agency_name": "agent_name"}, inplace=True)

for col in ["website", "email", "phone", "detail"]:
    if col not in df_all.columns:
        df_all[col] = None

if os.path.exists(OUTPUT_CSV):
    print(f"[RESUME] Found progress file. Loading completed records...")
    df_progress = pd.read_csv(OUTPUT_CSV)
    for index, row in df_progress.iterrows():
        if pd.notna(row.get("website")) or pd.notna(row.get("email")):
            df_all.at[index, "website"] = row.get("website")
            df_all.at[index, "email"] = row.get("email")
            df_all.at[index, "phone"] = row.get("phone")
            df_all.at[index, "detail"] = row.get("detail")

# -----------------------------
# REGEX & CLEANING UTILITIES
# -----------------------------
EMAIL_REGEX = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
PHONE_REGEX = r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+\d{9,13}|\b\d{3,5}[-\s]\d{3,5}[-\s]\d{3,5}\b"

def clean_extracted_emails(email_list):
    if not email_list: return None
    cleaned = []
    for email in email_list:
        email_clean = email.strip().lower().replace("%20", "")
        if any(email_clean.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"]): continue
        if "@2x" in email_clean or ( "email" in email_clean and len(email_clean) > 40 ): continue
        cleaned.append(email_clean)
    return ", ".join(list(set(cleaned))) if cleaned else None

def clean_extracted_phones(phone_list):
    if not phone_list: return None
    cleaned = []
    for phone in phone_list:
        phone_clean = phone.strip()
        if "0 0" in phone_clean or "360" in phone_clean: continue
        if "-" in phone_clean and len(phone_clean) > 15: continue
        if phone_clean.isdigit() and len(phone_clean) > 11: continue
        cleaned.append(phone_clean)
    return ", ".join(list(set(cleaned))) if cleaned else None

# -----------------------------
# METHOD 1: DYNAMIC DOMAIN EXTENSION MAKER
# -----------------------------
def get_predicted_urls(agent_name, country):
    # Remove junk acronym expressions from search strings to isolate target terms
    clean_name = str(agent_name).lower()
    clean_name = re.sub(r'\baka\b.*|\bpty\b.*|\bltd\b.*|\bllc\b.*', '', clean_name)
    clean_name = re.sub(r"[^a-zA-Z0-9]", "", clean_name).strip()
    
    if not clean_name: return []
    
    urls = [f"https://www.{clean_name}.com", f"https://{clean_name}.com"]
    clean_country = str(country).lower().strip()
    
    # Appends precise geographic extensions mapped across your specific records list
    if "bangladesh" in clean_country: urls.extend([f"https://www.{clean_name}.com.bd", f"https://{clean_name}.com.bd"])
    elif "australia" in clean_country: urls.extend([f"https://www.{clean_name}.com.au", f"https://{clean_name}.com.au"])
    elif "united kingdom" in clean_country or "uk" in clean_country: urls.extend([f"https://www.{clean_name}.co.uk", f"https://{clean_name}.uk"])
    elif "india" in clean_country: urls.extend([f"https://www.{clean_name}.in", f"https://{clean_name}.co.in"])
    elif "albania" in clean_country: urls.extend([f"https://www.{clean_name}.al", f"https://{clean_name}.al"])
    elif "argentina" in clean_country: urls.extend([f"https://www.{clean_name}.com.ar"])
    elif "bahrain" in clean_country: urls.extend([f"https://www.{clean_name}.bh", f"https://www.{clean_name}.com.bh"])
    elif "azerbaijan" in clean_country: urls.extend([f"https://www.{clean_name}.az"])
        
    return urls

# -----------------------------
# METHOD 2: BULLETPROOF GOOGLE CRAWL BACKUP
# -----------------------------
def get_google_search_fallback(page, query):
    # Standard query parsing string array mapping layout
    encoded = urllib.parse.quote_plus(query)
    search_url = f"https://google.com{encoded}"
    try:
        page.goto(search_url, timeout=12000)
        page.wait_for_timeout(2000)
        
        # Pull layout header anchors
        links = page.locator("a:has(h3)").all()
        for link in links:
            href = link.get_attribute("href")
            if href and href.startswith("http"):
                if any(domain in href.lower() for domain in [
                    "google.", "webcache.", "youtube.com", "facebook.com", 
                    "linkedin.com", "instagram.com", "twitter.com", "x.com"
                ]): continue
                return href
    except:
        pass
    return None

# -----------------------------
# CENTRAL SITE TEXT PARSER
# -----------------------------
def extract_info(page, url):
    if not url: return None, None, None
    try:
        page.goto(url, timeout=12000, wait_until="commit")
        page.wait_for_timeout(2000)

        raw_html = page.content()
        visible_text = page.locator("body").inner_text()
        detail_snippet = " ".join(visible_text.split()[:30]) if visible_text else ""
        detail_snippet = re.sub(r'[^\w\s,.?!\-]', '', detail_snippet).strip().replace("\n", " ")

        raw_emails = re.findall(EMAIL_REGEX, raw_html)
        raw_phones = re.findall(PHONE_REGEX, raw_html)

        emails = clean_extracted_emails(raw_emails)
        phones = clean_extracted_phones(raw_phones)

        return emails, phones, detail_snippet
    except:
        return None, None, None

# -----------------------------
# PIPELINE EXECUTION
# -----------------------------
print(f"\n[STARTING] Scanning collection targets array. Size: {len(df_all)} items...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True) # Runs smoothly in background
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
        locale="en-US"
    )
    page = context.new_page()

    for i, row in df_all.iterrows():
        # Check tracking parameters to verify skip triggers
        if pd.notna(row["website"]) and (pd.notna(row["email"]) or pd.notna(row["phone"])):
            continue

        agent = row["agent_name"]
        country = row["country"]

        print(f"\n[{i + 1}/{len(df_all)}] Processing Agency: '{agent}' ({country})")

        target_website = None
        final_email, final_phone, final_detail = None, None, None
        
        # Step 1: Sequential Domain Prediction Route
        predicted_urls = get_predicted_urls(agent, country)
        for pred_url in predicted_urls:
            email, phone, detail = extract_info(page, pred_url)
            if email or phone or (detail and len(detail) > 10):
                target_website = pred_url
                final_email, final_phone, final_detail = email, phone, detail
                print(f"   -> [DIRECT HIT] Found URL via domain guesser: {target_website}")
                break

        # Step 2: Google Search Fallback Route (Runs if Direct hits draw blank)
        if not target_website:
            print("   -> Direct checks missed. Deploying organic Google search query fallback...")
            search_query = f"{agent} {country} education consultancy official website"
            target_website = get_google_search_fallback(page, search_query)
            
            if target_website:
                print(f"   -> [SEARCH HIT] Resolved website via search logic: {target_website}")
                final_email, final_phone, final_detail = extract_info(page, target_website)

        # Commit item attributes back to persistence arrays
        df_all.at[i, "website"] = target_website
        df_all.at[i, "email"] = final_email
        df_all.at[i, "phone"] = final_phone
        df_all.at[i, "detail"] = final_detail

        # Save data progress safely on every iteration loop
        df_all.to_csv(OUTPUT_CSV, index=False)
        time.sleep(1)

    context.close()
    browser.close()

print(f"\n[COMPLETE] Scraping workflow wrapped up successfully! Location: {OUTPUT_CSV}")
