import os
import pandas as pd

# -----------------------------
# PATH CONFIGURATION
# -----------------------------
SCRAPED_CSV = r"E:\Soykot\Scraping\crawler\data\goldsmiths_final_output.csv"
CLEANED_CSV = r"E:\Soykot\Scraping\crawler\collect_CSV\goldsmiths_clean.csv"

# 1. Check if the scraped progress file exists
if not os.path.exists(SCRAPED_CSV):
    raise FileNotFoundError(
        f"Could not find the scraped progress file at: {SCRAPED_CSV}"
    )

# 2. Read the raw scraped dataframe
df = pd.read_csv(SCRAPED_CSV)
initial_rows = len(df)

# 3. Drop rows where the 'website' column is missing or NaN
df_cleaned = df.dropna(subset=["website"]).copy()

# 4. Remove rows where 'website' might be an empty string or spaces
df_cleaned = df_cleaned[df_cleaned["website"].str.strip() != ""]
final_rows = len(df_cleaned)

# 5. Save the final cleaned dataframe to the requested filename
df_cleaned.to_csv(CLEANED_CSV, index=False)

# 6. Display confirmation summary
print("\n" + "=" * 45)
print("SUCCESS: VALID URLS FILTERED & SAVED SUCCESSFULLY!")
print("=" * 45)
print(f"Total entries processed:  {initial_rows}")
print(f"Empty URLs dropped:       {initial_rows - final_rows}")
print(f"Saved Valid Agencies:     {final_rows}")
print(f"Destination Path:         {CLEANED_CSV}")
print("=" * 45 + "\n")
