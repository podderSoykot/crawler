"""
eda_analysis.py
===============
Exploratory Data Analysis for three university recruitment-agent datasets:
  - Essex    (essex_clean.csv)
  - Goldsmiths (goldsmiths_clean.csv)
  - SHU      (SHU_clean.csv)

Run:
    python eda_analysis.py

Outputs:
    All plots are saved as PNG files in the current working directory.
"""

import os
import warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")          # headless backend – no display required
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
from matplotlib.gridspec import GridSpec

warnings.filterwarnings("ignore")

# ── Style ──────────────────────────────────────────────────────────────────────
sns.set_theme(style="whitegrid", palette="muted", font_scale=1.05)
PALETTE = {"Essex": "#1f77b4", "Goldsmiths": "#ff7f0e", "SHU": "#2ca02c"}
FIG_DIR = "."          # change to a sub-folder if preferred
DPI = 150


def savefig(name: str):
    path = os.path.join(FIG_DIR, name)
    plt.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close()
    print(f"  saved → {path}")


# ══════════════════════════════════════════════════════════════════════════════
# 1. LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("1. LOADING DATA")
print("=" * 60)

FILE_MAP = {
    "Essex":      "essex_clean.csv",
    "Goldsmiths": "goldsmiths_clean.csv",
    "SHU":        "SHU_clean.csv",
}

# Try the uploads path first (cloud env), then fall back to local
UPLOAD_DIR = "/mnt/user-data/uploads"

raw: dict[str, pd.DataFrame] = {}
for label, fname in FILE_MAP.items():
    cloud_path = os.path.join(UPLOAD_DIR, fname)
    local_path = fname
    path = cloud_path if os.path.exists(cloud_path) else local_path
    raw[label] = pd.read_csv(path)
    print(f"  {label:12s} → {path}  |  shape: {raw[label].shape}")


# ══════════════════════════════════════════════════════════════════════════════
# 2. BASIC OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("2. BASIC OVERVIEW (shape, columns, dtypes)")
print("=" * 60)

for label, df in raw.items():
    print(f"\n── {label} ──")
    print(f"  Rows × Cols : {df.shape[0]} × {df.shape[1]}")
    print(f"  Columns     : {list(df.columns)}")
    print(df.dtypes.to_string())


# ══════════════════════════════════════════════════════════════════════════════
# 3. MISSING-VALUE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("3. MISSING VALUES")
print("=" * 60)

fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.suptitle("Missing Values per Column (%)", fontsize=14, fontweight="bold")

for ax, (label, df) in zip(axes, raw.items()):
    miss_pct = df.isnull().mean() * 100
    miss_pct = miss_pct[miss_pct > 0].sort_values(ascending=True)

    print(f"\n  {label}")
    for col, pct in miss_pct.items():
        print(f"    {col:15s}  {pct:6.1f}%  ({df[col].isnull().sum()} / {len(df)})")

    if miss_pct.empty:
        ax.text(0.5, 0.5, "No missing values", ha="center", va="center",
                transform=ax.transAxes)
    else:
        bars = ax.barh(miss_pct.index, miss_pct.values, color=PALETTE[label], alpha=0.8)
        ax.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=9)
        ax.set_xlim(0, 105)
        ax.set_xlabel("Missing %")

    ax.set_title(label, fontweight="bold", color=PALETTE[label])

plt.tight_layout()
savefig("01_missing_values.png")


# ══════════════════════════════════════════════════════════════════════════════
# 4. CONTACT FIELD COVERAGE  (email & phone)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("4. CONTACT FIELD COVERAGE")
print("=" * 60)

coverage_rows = []
for label, df in raw.items():
    n = len(df)
    for field in ["email", "phone"]:
        if field in df.columns:
            filled = df[field].notna().sum()
            pct = filled / n * 100
            coverage_rows.append({"Dataset": label, "Field": field,
                                   "Filled": filled, "Pct": pct})
            print(f"  {label:12s}  {field:6s}  {filled:4d}/{n}  ({pct:5.1f}% filled)")

cov_df = pd.DataFrame(coverage_rows)

fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(cov_df["Dataset"].unique()))
width = 0.35

email_df = cov_df[cov_df["Field"] == "email"].reset_index(drop=True)
phone_df = cov_df[cov_df["Field"] == "phone"].reset_index(drop=True)
datasets  = email_df["Dataset"].tolist()

b1 = ax.bar(x - width/2, email_df["Pct"], width, label="Email",
            color=[PALETTE[d] for d in datasets], alpha=0.9)
b2 = ax.bar(x + width/2, phone_df["Pct"], width, label="Phone",
            color=[PALETTE[d] for d in datasets], alpha=0.5, hatch="//")

ax.bar_label(b1, fmt="%.0f%%", padding=3, fontsize=9)
ax.bar_label(b2, fmt="%.0f%%", padding=3, fontsize=9)
ax.set_xticks(x)
ax.set_xticklabels(datasets)
ax.set_ylabel("% Agents with contact info")
ax.set_ylim(0, 115)
ax.set_title("Contact Field Coverage by Dataset", fontweight="bold")
ax.legend(title="Field")
plt.tight_layout()
savefig("02_contact_coverage.png")


# ══════════════════════════════════════════════════════════════════════════════
# 5. AGENTS PER DATASET
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("5. AGENT COUNT PER DATASET")
print("=" * 60)

counts = {label: len(df) for label, df in raw.items()}
for k, v in counts.items():
    print(f"  {k:12s}  {v:,} agents")

fig, ax = plt.subplots(figsize=(7, 4))
bars = ax.bar(counts.keys(), counts.values(),
              color=[PALETTE[k] for k in counts], edgecolor="white", linewidth=1.2)
ax.bar_label(bars, fmt="%d", padding=5, fontsize=11, fontweight="bold")
ax.set_ylabel("Number of Agents")
ax.set_title("Total Agents per Dataset", fontweight="bold")
ax.set_ylim(0, max(counts.values()) * 1.15)
plt.tight_layout()
savefig("03_agent_counts.png")


# ══════════════════════════════════════════════════════════════════════════════
# 6. COUNTRY DISTRIBUTION (Top-N per dataset)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("6. COUNTRY DISTRIBUTION (Top 15)")
print("=" * 60)

TOP_N = 15
fig, axes = plt.subplots(1, 3, figsize=(20, 7))
fig.suptitle(f"Top {TOP_N} Countries by Agent Count", fontsize=14, fontweight="bold")

for ax, (label, df) in zip(axes, raw.items()):
    top = df["country"].value_counts().head(TOP_N)
    print(f"\n  {label}")
    print(top.to_string())
    bars = ax.barh(top.index[::-1], top.values[::-1],
                   color=PALETTE[label], alpha=0.85)
    ax.bar_label(bars, padding=3, fontsize=8)
    ax.set_xlabel("Number of Agents")
    ax.set_title(label, fontweight="bold", color=PALETTE[label])

plt.tight_layout()
savefig("04_top_countries.png")


# ══════════════════════════════════════════════════════════════════════════════
# 7. UNIQUE COUNTRIES PER DATASET
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("7. UNIQUE COUNTRIES")
print("=" * 60)

uni_countries = {label: df["country"].nunique() for label, df in raw.items()}
for k, v in uni_countries.items():
    print(f"  {k:12s}  {v} unique countries")

fig, ax = plt.subplots(figsize=(7, 4))
bars = ax.bar(uni_countries.keys(), uni_countries.values(),
              color=[PALETTE[k] for k in uni_countries], edgecolor="white")
ax.bar_label(bars, padding=5, fontsize=11, fontweight="bold")
ax.set_ylabel("Unique Countries")
ax.set_title("Geographic Reach (Unique Countries)", fontweight="bold")
ax.set_ylim(0, max(uni_countries.values()) * 1.2)
plt.tight_layout()
savefig("05_unique_countries.png")


# ══════════════════════════════════════════════════════════════════════════════
# 8. OVERLAP: SHARED COUNTRIES ACROSS DATASETS
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("8. COUNTRY OVERLAP ACROSS DATASETS")
print("=" * 60)

country_sets = {label: set(df["country"].dropna()) for label, df in raw.items()}
labels = list(country_sets.keys())

pairs = [(labels[i], labels[j])
         for i in range(len(labels)) for j in range(i+1, len(labels))]

print("  Pairwise overlaps:")
for a, b in pairs:
    shared = country_sets[a] & country_sets[b]
    print(f"    {a} ∩ {b}: {len(shared)} countries")

all_shared = country_sets[labels[0]] & country_sets[labels[1]] & country_sets[labels[2]]
print(f"  All three:  {len(all_shared)} countries")

# Euler-style bar showing intersection sizes
overlap_data = {}
for a, b in pairs:
    key = f"{a}\n∩ {b}"
    overlap_data[key] = len(country_sets[a] & country_sets[b])
overlap_data["All\nthree"] = len(all_shared)

fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(overlap_data.keys(), overlap_data.values(),
       color=["steelblue", "darkorange", "seagreen", "crimson"],
       edgecolor="white", alpha=0.85)
for i, (k, v) in enumerate(overlap_data.items()):
    ax.text(i, v + 0.5, str(v), ha="center", va="bottom", fontweight="bold")
ax.set_ylabel("Shared Countries")
ax.set_title("Country Overlap Between Datasets", fontweight="bold")
plt.tight_layout()
savefig("06_country_overlap.png")


# ══════════════════════════════════════════════════════════════════════════════
# 9. AGENTS PER COUNTRY – DISTRIBUTIONS
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("9. AGENTS-PER-COUNTRY DISTRIBUTION")
print("=" * 60)

fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle("Distribution of Agents per Country", fontsize=14, fontweight="bold")

for ax, (label, df) in zip(axes, raw.items()):
    per_country = df["country"].value_counts()
    print(f"\n  {label}")
    print(per_country.describe().to_string())
    ax.hist(per_country.values, bins=20, color=PALETTE[label], alpha=0.8, edgecolor="white")
    ax.axvline(per_country.mean(), color="red", linestyle="--",
               linewidth=1.5, label=f"Mean={per_country.mean():.1f}")
    ax.axvline(per_country.median(), color="orange", linestyle="-.",
               linewidth=1.5, label=f"Median={per_country.median():.1f}")
    ax.set_xlabel("Agents per Country")
    ax.set_ylabel("Number of Countries")
    ax.set_title(label, fontweight="bold", color=PALETTE[label])
    ax.legend(fontsize=8)

plt.tight_layout()
savefig("07_agents_per_country_dist.png")


# ══════════════════════════════════════════════════════════════════════════════
# 10. WEBSITE PRESENCE
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("10. WEBSITE PRESENCE")
print("=" * 60)

website_data = {}
for label, df in raw.items():
    if "website" in df.columns:
        has = df["website"].notna() & (df["website"].str.strip() != "")
        pct = has.sum() / len(df) * 100
        website_data[label] = pct
        print(f"  {label:12s}  {has.sum()}/{len(df)}  ({pct:.1f}% with website)")

if website_data:
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(website_data.keys(), website_data.values(),
                  color=[PALETTE[k] for k in website_data], alpha=0.85, edgecolor="white")
    ax.bar_label(bars, fmt="%.1f%%", padding=4, fontsize=11, fontweight="bold")
    ax.set_ylabel("% Agents with Website")
    ax.set_ylim(0, 115)
    ax.set_title("Website Presence by Dataset", fontweight="bold")
    plt.tight_layout()
    savefig("08_website_presence.png")


# ══════════════════════════════════════════════════════════════════════════════
# 11. ADDRESS COVERAGE (SHU & Goldsmiths only)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("11. ADDRESS COVERAGE")
print("=" * 60)

addr_data = {}
for label, df in raw.items():
    if "address" in df.columns:
        has = df["address"].notna() & (df["address"].str.strip() != "")
        pct = has.sum() / len(df) * 100
        addr_data[label] = pct
        print(f"  {label:12s}  {has.sum()}/{len(df)}  ({pct:.1f}% with address)")

if addr_data:
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(addr_data.keys(), addr_data.values(),
                  color=[PALETTE[k] for k in addr_data], alpha=0.85, edgecolor="white")
    ax.bar_label(bars, fmt="%.1f%%", padding=4, fontsize=11, fontweight="bold")
    ax.set_ylabel("% Agents with Address")
    ax.set_ylim(0, 115)
    ax.set_title("Address Coverage by Dataset", fontweight="bold")
    plt.tight_layout()
    savefig("09_address_coverage.png")


# ══════════════════════════════════════════════════════════════════════════════
# 12. COMBINED COMPLETENESS HEATMAP
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("12. COMPLETENESS HEATMAP")
print("=" * 60)

ALL_COLS = ["country", "agent_name", "website", "email", "phone", "address", "detail"]
heat_data = {}
for label, df in raw.items():
    row = {}
    for col in ALL_COLS:
        if col in df.columns:
            row[col] = round((df[col].notna() & (df[col].astype(str).str.strip() != "")).mean() * 100, 1)
        else:
            row[col] = float("nan")
    heat_data[label] = row

heat_df = pd.DataFrame(heat_data).T[ALL_COLS]
print(heat_df.to_string())

fig, ax = plt.subplots(figsize=(11, 4))
mask = heat_df.isna()
sns.heatmap(heat_df.astype(float), annot=True, fmt=".0f", cmap="YlGn",
            linewidths=0.5, linecolor="white",
            vmin=0, vmax=100, ax=ax, mask=mask,
            cbar_kws={"label": "% Filled"})
ax.set_title("Field Completeness (%) per Dataset", fontweight="bold")
ax.set_xlabel("Field")
ax.set_ylabel("Dataset")
plt.tight_layout()
savefig("10_completeness_heatmap.png")


# ══════════════════════════════════════════════════════════════════════════════
# 13. DUPLICATE AGENT NAMES (within & across datasets)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("13. DUPLICATE AGENT NAMES")
print("=" * 60)

name_col_map = {"Essex": "agent_name", "Goldsmiths": "agent_name", "SHU": "agency_name"}

print("  Within-dataset duplicates:")
for label, df in raw.items():
    col = name_col_map[label]
    dupes = df[col].str.strip().str.lower().duplicated().sum()
    print(f"    {label:12s}  {dupes} duplicate entries")

print("\n  Cross-dataset: agents appearing in multiple datasets")
name_sets = {}
for label, df in raw.items():
    col = name_col_map[label]
    name_sets[label] = set(df[col].dropna().str.strip().str.lower())

for a, b in pairs:
    shared_names = name_sets[a] & name_sets[b]
    print(f"    {a} ∩ {b}: {len(shared_names)} shared agent names")

all_shared_names = name_sets["Essex"] & name_sets["Goldsmiths"] & name_sets["SHU"]
print(f"    All three: {len(all_shared_names)} shared agent names")


# ══════════════════════════════════════════════════════════════════════════════
# 14. SUMMARY TABLE
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("14. SUMMARY TABLE")
print("=" * 60)

summary_rows = []
for label, df in raw.items():
    col = name_col_map[label]
    row = {
        "Dataset": label,
        "Total Agents": len(df),
        "Unique Countries": df["country"].nunique(),
        "Email %": f"{df['email'].notna().mean()*100:.1f}%" if "email" in df.columns else "N/A",
        "Phone %": f"{df['phone'].notna().mean()*100:.1f}%" if "phone" in df.columns else "N/A",
        "Website %": f"{(df['website'].notna() & df['website'].str.strip().ne('')).mean()*100:.1f}%"
                     if "website" in df.columns else "N/A",
        "Address %": f"{(df['address'].notna() & df['address'].str.strip().ne('')).mean()*100:.1f}%"
                     if "address" in df.columns else "N/A",
    }
    summary_rows.append(row)

summary_df = pd.DataFrame(summary_rows).set_index("Dataset")
print(summary_df.to_string())

# Save summary as CSV
out_path = os.path.join(FIG_DIR, "00_summary_table.csv")
summary_df.to_csv(out_path)
print(f"\n  saved → {out_path}")


# ══════════════════════════════════════════════════════════════════════════════
# DONE
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("EDA COMPLETE")
print("=" * 60)
print("\nFiles written:")
for fname in sorted(os.listdir(FIG_DIR)):
    if fname.startswith(("00_", "01_", "02_", "03_", "04_", "05_",
                          "06_", "07_", "08_", "09_", "10_")):
        print(f"  {fname}")