"""Clean the EEA EU ETS database (Union Registry extract) into a tidy table for Power BI.

Input : data/raw/ETS_Database_September_2026.xlsx  (EEA datahub download)
Output: data/clean/ets_fact.csv, data/clean/dim_country.csv, data/clean/dim_activity.csv
"""
import pandas as pd
from pathlib import Path

RAW = Path("data/raw/ETS_Database_September_2026.xlsx")
OUT = Path("data/clean"); OUT.mkdir(parents=True, exist_ok=True)

# Metrics kept for the dashboard (citl_information -> short name)
METRICS = {
    "2. Verified emissions": "verified_emissions",
    "1.1 Freely allocated allowances": "free_allocation",
    "4. Total surrendered units": "surrendered_units",
}
# Pre-aggregated activity codes in the source: dropping them avoids double counting
AGGREGATE_CODES = {"20-99", "21-99"}

COUNTRIES = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "HR": "Croatia", "CY": "Cyprus",
    "CZ": "Czechia", "DK": "Denmark", "EE": "Estonia", "FI": "Finland", "FR": "France",
    "DE": "Germany", "GR": "Greece", "HU": "Hungary", "IE": "Ireland", "IT": "Italy",
    "LV": "Latvia", "LT": "Lithuania", "LU": "Luxembourg", "MT": "Malta", "NL": "Netherlands",
    "PL": "Poland", "PT": "Portugal", "RO": "Romania", "SK": "Slovakia", "SI": "Slovenia",
    "ES": "Spain", "SE": "Sweden", "IS": "Iceland", "LI": "Liechtenstein", "NO": "Norway",
    "XI": "Northern Ireland", "GB": "United Kingdom",
}

df = pd.read_excel(RAW, dtype={"main_activity_code": str})

# 1) keep yearly rows only (the source also has "Total ... trading period" rows)
df["year"] = pd.to_numeric(df["year"], errors="coerce")
df = df.dropna(subset=["year"]).astype({"year": int})

# 2) keep real countries only (drops Innovation fund, RRF, NER 300 ...)
df = df[df["country_code"].isin(COUNTRIES)]

# 3) keep chosen metrics, drop aggregate activity codes
df = df[df["citl_information"].isin(METRICS) & ~df["main_activity_code"].isin(AGGREGATE_CODES)]
df["metric"] = df["citl_information"].map(METRICS)

fact = (df.rename(columns={"main_activity_code": "activity_code"})
          [["country_code", "activity_code", "year", "metric", "value"]]
          .assign(value_mt=lambda d: d["value"] / 1e6))
fact["is_aviation"] = fact["activity_code"].eq("10")
fact.to_csv(OUT / "ets_fact.csv", index=False)

pd.DataFrame({"country_code": list(COUNTRIES), "country": list(COUNTRIES.values())}
             ).to_csv(OUT / "dim_country.csv", index=False)
pd.DataFrame({"activity_code": sorted(fact["activity_code"].unique()),
              "activity_label": ""}  # fill from EEA "Translation of activity codes" file
             ).to_csv(OUT / "dim_activity.csv", index=False)

# sanity check: EU total of detailed stationary codes must equal the source 20-99 aggregate
chk = (fact[(fact.metric == "verified_emissions") & ~fact.activity_code.isin(["10", "50"])]
       .groupby("year")["value_mt"].sum())
print(chk.loc[2013:2025].round(1))
