"""
eda_office_intelligence.py
==========================
Exploratory Data Analysis for office_intelligence_v25.csv
— the scraped sub-agent / office dataset produced by scrape_v25.py

Run:
    python eda_office_intelligence.py

Outputs (saved in the same folder as this script):
    eda_01_overview.png
    eda_02_missing_values.png
    eda_03_records_per_agent.png
    eda_04_duplicate_analysis.png
    eda_05_top_countries.png
    eda_06_country_normalisation.png
    eda_07_top_cities.png
    eda_08_field_coverage_per_agent.png
    eda_09_phone_quality.png
    eda_10_email_domains.png
    eda_11_geo_heatmap.png
    eda_12_clean_summary.csv
"""

import os
import re
import warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from collections import Counter

warnings.filterwarnings("ignore")

# ── Style ──────────────────────────────────────────────────────────────────────
sns.set_theme(style="whitegrid", palette="muted", font_scale=1.05)
DPI     = 150
OUT_DIR = "."          # change if you want plots in a sub-folder

ACCENT  = "#185FA5"    # blue
ACCENT2 = "#1D9E75"    # teal
WARN    = "#BA7517"    # amber
DANGER  = "#A32D2D"    # red
NEUTRAL = "#888780"    # gray

def savefig(name):
    path = os.path.join(OUT_DIR, name)
    plt.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close()
    print(f"  saved → {path}")


# ══════════════════════════════════════════════════════════════════════════════
# 0. LOAD
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("0. LOADING DATA")
print("="*60)

# Try cloud path first, then local
PATHS = [
    "/mnt/user-data/uploads/office_intelligence_v25.csv",
    "office_intelligence_v25.csv",
]
df = None
for p in PATHS:
    if os.path.exists(p):
        df = pd.read_csv(p)
        print(f"  Loaded: {p}")
        break
if df is None:
    raise FileNotFoundError("office_intelligence_v25.csv not found. "
                            "Place it alongside this script or at the cloud path.")

print(f"  Shape : {df.shape[0]:,} rows × {df.shape[1]} columns")
print(f"  Cols  : {list(df.columns)}")


# ══════════════════════════════════════════════════════════════════════════════
# 1. BASIC OVERVIEW  (printed only)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("1. BASIC OVERVIEW")
print("="*60)
print(f"  Total rows         : {len(df):,}")
print(f"  Unique agents      : {df['agent_name'].nunique()}")
print(f"  Unique source URLs : {df['source_page'].nunique():,}")
print("\n  First 5 rows:")
print(df.head().to_string())
print("\n  dtypes:")
print(df.dtypes.to_string())


# ══════════════════════════════════════════════════════════════════════════════
# 2. MISSING VALUE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("2. MISSING VALUE ANALYSIS")
print("="*60)

miss = df.isnull().sum()
miss_pct = df.isnull().mean() * 100
miss_df = pd.DataFrame({"missing": miss, "pct": miss_pct}).sort_values("pct", ascending=True)
print(miss_df.to_string())

fig, ax = plt.subplots(figsize=(9, 4))
bars = ax.barh(miss_df.index, miss_df["pct"], color=ACCENT, alpha=0.85, edgecolor="white")
ax.bar_label(bars, fmt="%.1f%%", padding=4, fontsize=10, fontweight="bold")
ax.set_xlim(0, 115)
ax.set_xlabel("% Missing")
ax.set_title("Missing Values per Column", fontweight="bold")
plt.tight_layout()
savefig("eda_02_missing_values.png")


# ══════════════════════════════════════════════════════════════════════════════
# 3. RECORDS PER AGENT
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("3. RECORDS PER AGENT")
print("="*60)

rec_per_agent = df["agent_name"].value_counts()
print(f"  Min : {rec_per_agent.min()}")
print(f"  Max : {rec_per_agent.max()}")
print(f"  Mean: {rec_per_agent.mean():.1f}")
print(f"\n  Top 20 agents:")
print(rec_per_agent.head(20).to_string())

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Bar: top 20
top20 = rec_per_agent.head(20)
axes[0].barh(top20.index[::-1], top20.values[::-1], color=ACCENT, alpha=0.85)
axes[0].set_xlabel("Record count")
axes[0].set_title("Top 20 Agents by Record Count", fontweight="bold")
for i, v in enumerate(top20.values[::-1]):
    axes[0].text(v + 5, i, str(v), va="center", fontsize=8)

# Histogram: distribution
axes[1].hist(rec_per_agent.values, bins=20, color=ACCENT2, alpha=0.85, edgecolor="white")
axes[1].axvline(rec_per_agent.mean(), color=WARN, linestyle="--", linewidth=2,
                label=f"Mean={rec_per_agent.mean():.0f}")
axes[1].axvline(rec_per_agent.median(), color=DANGER, linestyle="-.", linewidth=2,
                label=f"Median={rec_per_agent.median():.0f}")
axes[1].set_xlabel("Records per agent")
axes[1].set_ylabel("Number of agents")
axes[1].set_title("Distribution of Record Counts", fontweight="bold")
axes[1].legend()
plt.tight_layout()
savefig("eda_03_records_per_agent.png")


# ══════════════════════════════════════════════════════════════════════════════
# 4. DUPLICATE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("4. DUPLICATE ANALYSIS")
print("="*60)

total   = len(df)
dup_all = df.duplicated().sum()
dup_key = df.duplicated(subset=["agent_name","country","city","phones"]).sum()
dup_ph  = df.duplicated(subset=["agent_name","phones"]).sum()

print(f"  Exact duplicates (all cols)          : {dup_all:,}  ({dup_all/total*100:.1f}%)")
print(f"  Duplicates (agent+country+city+phone): {dup_key:,}  ({dup_key/total*100:.1f}%)")
print(f"  Duplicates (agent+phone)             : {dup_ph:,}  ({dup_ph/total*100:.1f}%)")
print(f"  After dedup (agent+phone key)        : {total-dup_ph:,} unique rows")

categories = ["Raw rows", "After exact dedup", "After key dedup", "After agent+phone dedup"]
values     = [total, total-dup_all, total-dup_key, total-dup_ph]

fig, ax = plt.subplots(figsize=(10, 4))
colors = [ACCENT, ACCENT2, WARN, DANGER]
bars = ax.bar(categories, values, color=colors, alpha=0.85, edgecolor="white")
ax.bar_label(bars, fmt="%,.0f", padding=4, fontweight="bold", fontsize=10)
ax.set_ylabel("Row count")
ax.set_title("Row Count at Each Deduplication Stage", fontweight="bold")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:,.0f}"))
plt.tight_layout()
savefig("eda_04_duplicate_analysis.png")


# ══════════════════════════════════════════════════════════════════════════════
# 5. COUNTRY DISTRIBUTION (raw)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("5. TOP COUNTRIES (raw)")
print("="*60)

top_countries = df["country"].value_counts().head(20)
print(top_countries.to_string())

fig, ax = plt.subplots(figsize=(10, 7))
ax.barh(top_countries.index[::-1], top_countries.values[::-1], color=ACCENT, alpha=0.85)
for i, v in enumerate(top_countries.values[::-1]):
    ax.text(v + 3, i, str(v), va="center", fontsize=9)
ax.set_xlabel("Record count")
ax.set_title("Top 20 Countries (raw — before normalisation)", fontweight="bold")
plt.tight_layout()
savefig("eda_05_top_countries.png")


# ══════════════════════════════════════════════════════════════════════════════
# 6. COUNTRY NORMALISATION — the UK / United Kingdom / uk problem
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("6. COUNTRY NORMALISATION")
print("="*60)

COUNTRY_MAP = {
    "uk": "United Kingdom", "UK": "United Kingdom",
    "usa": "United States", "USA": "United States",
    "United States of America": "United States",
    "uae": "United Arab Emirates", "UAE": "United Arab Emirates",
    "UNITED KINGDOM": "United Kingdom", "INDIA": "India",
    "AUSTRALIA": "Australia", "MALAYSIA": "Malaysia",
    "TURKEY": "Turkey", "ARGENTINA": "Argentina",
    "peru": "Peru", "mexico": "Mexico", "chile": "Chile",
    "bahrain": "Bahrain", "bangladesh": "Bangladesh",
    "india": "India", "kuwait": "Kuwait",
    "malaysia": "Malaysia", "morocco": "Morocco",
    "nepal": "Nepal", "nigeria": "Nigeria",
    "pakistan": "Pakistan", "romania": "Romania",
    "singapore": "singapore",
}

df["country_norm"] = df["country"].map(COUNTRY_MAP).fillna(df["country"])

# Show how many rows changed
changed = (df["country_norm"] != df["country"]).sum()
print(f"  Rows changed by normalisation: {changed:,}")

top_norm = df["country_norm"].value_counts().head(20)
print("\n  Top 20 countries after normalisation:")
print(top_norm.to_string())

fig, axes = plt.subplots(1, 2, figsize=(16, 7))
for ax, data, title in zip(
    axes,
    [df["country"].value_counts().head(15), top_norm.head(15)],
    ["Before normalisation (top 15)", "After normalisation (top 15)"],
):
    ax.barh(data.index[::-1], data.values[::-1], color=ACCENT, alpha=0.85)
    for i, v in enumerate(data.values[::-1]):
        ax.text(v + 1, i, str(v), va="center", fontsize=9)
    ax.set_title(title, fontweight="bold")
    ax.set_xlabel("Record count")

plt.suptitle("Country Normalisation Effect", fontweight="bold", y=1.01)
plt.tight_layout()
savefig("eda_06_country_normalisation.png")


# ══════════════════════════════════════════════════════════════════════════════
# 7. TOP CITIES
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("7. TOP CITIES")
print("="*60)

top_cities = df["city"].value_counts().head(20)
print(top_cities.to_string())

fig, ax = plt.subplots(figsize=(10, 7))
ax.barh(top_cities.index[::-1], top_cities.values[::-1], color=ACCENT2, alpha=0.85)
for i, v in enumerate(top_cities.values[::-1]):
    ax.text(v + 1, i, str(v), va="center", fontsize=9)
ax.set_xlabel("Record count")
ax.set_title("Top 20 Cities", fontweight="bold")
plt.tight_layout()
savefig("eda_07_top_cities.png")


# ══════════════════════════════════════════════════════════════════════════════
# 8. FIELD COVERAGE PER AGENT
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("8. FIELD COVERAGE PER AGENT")
print("="*60)

def coverage(series):
    return series.notna().mean() * 100

agent_cov = df.groupby("agent_name").agg(
    records     =("agent_name", "count"),
    email_pct   =("emails",    coverage),
    phone_pct   =("phones",    coverage),
    country_pct =("country",   coverage),
    city_pct    =("city",      coverage),
).sort_values("records", ascending=False)

print(agent_cov.head(20).to_string())

# Heatmap: top 30 agents
top30 = agent_cov.head(30)[["email_pct","phone_pct","country_pct","city_pct"]]

fig, ax = plt.subplots(figsize=(10, 11))
sns.heatmap(
    top30.astype(float),
    annot=True, fmt=".0f", cmap="YlGn",
    vmin=0, vmax=100, linewidths=0.5, linecolor="white",
    cbar_kws={"label": "% Filled"}, ax=ax,
)
ax.set_title("Field Coverage (%) — Top 30 Agents by Record Count", fontweight="bold")
ax.set_xlabel("")
plt.tight_layout()
savefig("eda_08_field_coverage_per_agent.png")


# ══════════════════════════════════════════════════════════════════════════════
# 9. PHONE QUALITY ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("9. PHONE QUALITY ANALYSIS")
print("="*60)

JUNK_PATTERNS = [
    re.compile(r"^\d{4}[-\.]\d{2}[-\.]\d{2}"),      # dates: 2026-06-04
    re.compile(r"\d \d \d \d \d \d"),                 # sequential spaced digits
    re.compile(r"^\d{4}\.\d{2}$"),                    # partial dates
    re.compile(r"^[0-9](\s[0-9]){5,}$"),              # "1 2 3 4 5 6 7"
    re.compile(r"\d{4} - \d{4}"),                     # year ranges
]

def phone_category(val):
    if pd.isna(val):
        return "missing"
    first = str(val).split(";")[0].strip()
    for pat in JUNK_PATTERNS:
        if pat.search(first):
            return "junk (date/seq)"
    digits = re.sub(r"\D","",first)
    if len(digits) < 7:
        return "too short (<7 digits)"
    if len(digits) > 15:
        return "too long (>15 digits)"
    return "valid"

df["phone_quality"] = df["phones"].apply(phone_category)
pq = df["phone_quality"].value_counts()
print(pq.to_string())

fig, ax = plt.subplots(figsize=(8, 4))
colors_map = {
    "valid": ACCENT2,
    "missing": NEUTRAL,
    "junk (date/seq)": DANGER,
    "too short (<7 digits)": WARN,
    "too long (>15 digits)": ACCENT,
}
bar_colors = [colors_map.get(k, NEUTRAL) for k in pq.index]
bars = ax.bar(pq.index, pq.values, color=bar_colors, edgecolor="white", alpha=0.9)
ax.bar_label(bars, fmt="%d", padding=4, fontweight="bold")
ax.set_ylabel("Row count")
ax.set_title("Phone Number Quality Classification", fontweight="bold")
ax.set_xticklabels(pq.index, rotation=15, ha="right")
plt.tight_layout()
savefig("eda_09_phone_quality.png")


# ══════════════════════════════════════════════════════════════════════════════
# 10. EMAIL DOMAIN ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("10. EMAIL DOMAIN ANALYSIS")
print("="*60)

def extract_domains(val):
    if pd.isna(val):
        return []
    return [e.split("@")[1].lower() for e in str(val).split(";")
            if "@" in e and len(e.split("@")) == 2]

all_domains = []
df["emails"].dropna().apply(lambda v: all_domains.extend(extract_domains(v)))
domain_counts = Counter(all_domains)
top_domains = pd.Series(dict(domain_counts.most_common(20)))

print(f"  Total email addresses extracted: {sum(domain_counts.values()):,}")
print(f"  Unique domains                 : {len(domain_counts):,}")
print("\n  Top 20 domains:")
print(top_domains.to_string())

# Flag known generic / junk domains
GENERIC_DOMAINS = {"gmail.com","yahoo.com","yahoo.co.uk","hotmail.com",
                   "outlook.com","company.com","domain.com","example.com",
                   "godaddy.com","lcig.io"}

fig, ax = plt.subplots(figsize=(10, 7))
bar_colors = [DANGER if d in GENERIC_DOMAINS else ACCENT for d in top_domains.index]
ax.barh(top_domains.index[::-1], top_domains.values[::-1], color=bar_colors[::-1], alpha=0.85)
for i, v in enumerate(top_domains.values[::-1]):
    ax.text(v + 0.5, i, str(v), va="center", fontsize=9)
ax.set_xlabel("Frequency")
ax.set_title("Top 20 Email Domains\n(red = generic / non-specific domain)", fontweight="bold")
plt.tight_layout()
savefig("eda_10_email_domains.png")


# ══════════════════════════════════════════════════════════════════════════════
# 11. GEO COVERAGE HEATMAP (agents × countries)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("11. GEO COVERAGE HEATMAP")
print("="*60)

# Use normalised country, top 20 agents × top 15 countries
top_agents   = df["agent_name"].value_counts().head(20).index
top_cntrs    = df["country_norm"].value_counts().head(15).index

sub = df[df["agent_name"].isin(top_agents) & df["country_norm"].isin(top_cntrs)]
pivot = sub.groupby(["agent_name","country_norm"]).size().unstack(fill_value=0)
# Only keep agents and countries that actually appear in pivot
valid_agents  = [a for a in top_agents  if a in pivot.index]
valid_cntrs   = [c for c in top_cntrs   if c in pivot.columns]
pivot = pivot.loc[valid_agents, valid_cntrs]

print(f"  Pivot shape: {pivot.shape}")
print(pivot.to_string())

fig, ax = plt.subplots(figsize=(14, 8))
sns.heatmap(
    pivot, annot=True, fmt="d", cmap="Blues",
    linewidths=0.5, linecolor="white",
    cbar_kws={"label": "Record count"}, ax=ax,
)
ax.set_title("Agent × Country Presence (top 20 agents × top 15 countries)",
             fontweight="bold")
ax.set_xlabel("Country")
ax.set_ylabel("Agent")
plt.tight_layout()
savefig("eda_11_geo_heatmap.png")


# ══════════════════════════════════════════════════════════════════════════════
# 12. CLEAN SUMMARY CSV
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("12. CLEAN SUMMARY CSV")
print("="*60)

# Deduplicated view: keep best row per agent+country+city+phone
clean = df[df["phone_quality"] == "valid"].copy()
clean["_key"] = (
    clean["agent_name"].fillna("") + "||" +
    clean["country_norm"].fillna("") + "||" +
    clean["city"].fillna("") + "||" +
    clean["phones"].fillna("")
)
clean["_score"] = clean["emails"].notna().astype(int)*2 + clean["country"].notna().astype(int)
clean = clean.sort_values("_score", ascending=False)
deduped = (
    clean.drop_duplicates(subset="_key", keep="first")
    .drop(columns=["_key","_score","phone_quality","country_norm"])
    .sort_values(["agent_name","country","city"])
    .reset_index(drop=True)
)

out_path = os.path.join(OUT_DIR, "eda_12_clean_summary.csv")
deduped.to_csv(out_path, index=False)
print(f"  Clean rows : {len(deduped):,}")
print(f"  Saved      : {out_path}")

# Final summary stats
print("\n  Clean data field coverage:")
for col in ["country","city","emails","phones"]:
    n = deduped[col].notna().sum()
    print(f"    {col:12s}: {n:,} / {len(deduped):,}  ({n/len(deduped)*100:.1f}%)")


# ══════════════════════════════════════════════════════════════════════════════
# OVERVIEW CARD (Fig 1 — printed summary visual)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("GENERATING OVERVIEW CARD")
print("="*60)

stats = {
    "Raw rows":            f"{len(df):,}",
    "Unique agents":       str(df["agent_name"].nunique()),
    "With phone":          f"{(df['phone_quality']=='valid').sum():,}",
    "With email":          f"{df['emails'].notna().sum():,}",
    "With country":        f"{df['country'].notna().sum():,}",
    "With city":           f"{df['city'].notna().sum():,}",
    "Unique countries":    str(df["country_norm"].nunique()),
    "Unique cities":       str(df["city"].nunique()),
    "Junk/date phones":    str((df["phone_quality"]=="junk (date/seq)").sum()),
    "Dedup rows (clean)":  f"{len(deduped):,}",
}

fig, ax = plt.subplots(figsize=(10, 5))
ax.axis("off")
y, x_label, x_val = 0.95, 0.05, 0.55
ax.text(0.5, 1.02, "office_intelligence_v25.csv — EDA Summary",
        ha="center", va="bottom", fontsize=14, fontweight="bold",
        transform=ax.transAxes)
for label, value in stats.items():
    ax.text(x_label, y, label, transform=ax.transAxes,
            fontsize=11, color="#5F5E5A")
    ax.text(x_val, y, value, transform=ax.transAxes,
            fontsize=11, fontweight="bold", color="#1A1917")
    y -= 0.09
plt.tight_layout()
savefig("eda_01_overview.png")


# ══════════════════════════════════════════════════════════════════════════════
# DONE
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("EDA COMPLETE — Files written:")
print("="*60)
for f in sorted(os.listdir(OUT_DIR)):
    if f.startswith("eda_"):
        size = os.path.getsize(os.path.join(OUT_DIR, f))
        print(f"  {f:<45} {size/1024:>6.1f} KB")