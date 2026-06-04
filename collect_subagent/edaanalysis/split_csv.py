import csv
import os
import re
from collections import defaultdict

INPUT_FILE = r"E:\Soykot\Scraping\crawler\collect_subagent\office_intelligence_v25.csv"
OUTPUT_DIR = r"E:\Soykot\Scraping\crawler\collect_subagent\agent_csvs"

def safe_filename(name):
    name = name.replace("\u00a0", " ").strip()
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = re.sub(r"\s+", "_", name)
    return name[:80]

print(f"Reading: {INPUT_FILE}\n")

rows_by_agent = defaultdict(list)

with open(INPUT_FILE, encoding="utf-8-sig", newline="") as f:
    reader     = csv.DictReader(f)
    fieldnames = reader.fieldnames
    print(f"Columns : {fieldnames}")

    for row in reader:
        agent = row["agent_name"].replace("\u00a0", " ").strip()
        rows_by_agent[agent].append(row)

total_rows   = sum(len(v) for v in rows_by_agent.values())
total_agents = len(rows_by_agent)
print(f"Rows    : {total_rows:,}")
print(f"Agents  : {total_agents}\n")

os.makedirs(OUTPUT_DIR, exist_ok=True)

results = []
for agent, agent_rows in rows_by_agent.items():
    fname = safe_filename(agent) + ".csv"
    fpath = os.path.join(OUTPUT_DIR, fname)
    with open(fpath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(agent_rows)
    results.append((agent, len(agent_rows), fname))

results.sort(key=lambda x: -x[1])

print(f"{'#':<4} {'Rows':>6}  {'Agent':<50}  File")
print("─" * 110)
for i, (agent, count, fname) in enumerate(results, 1):
    print(f"{i:<4} {count:>6,}  {agent:<50}  {fname}")
print("─" * 110)
print(f"\n✓ Done — {len(results)} CSV files written to:\n  {OUTPUT_DIR}")