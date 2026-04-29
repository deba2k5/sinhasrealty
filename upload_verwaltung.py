"""
Upload Verwaltung Contacts data to MongoDB.
Reads Verwaltung_Contacts_SINHAS-Final.xlsx and pushes both sheets:
  - VERWALTUNG CONTACTS  →  collection: verwaltung_contacts
  - AGENCY SUMMARY       →  collection: agency_summary
"""

import os
import pandas as pd
from pymongo import MongoClient
import certifi
import math
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://sinhasrealty:sinhasrealty@sinhasrealty.cqt4cec.mongodb.net/?appName=sinhasrealty"
)

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=10000)
db = client["sinharealty"]

EXCEL_PATH = "Verwaltung_Contacts_SINHAS-Final.xlsx"


def clean_val(v):
    """Convert NaN / float NaN to None for MongoDB."""
    if v is None:
        return None
    try:
        if isinstance(v, float) and math.isnan(v):
            return None
    except Exception:
        pass
    return v


# ────────────────────────────────────────────────────────
# 1. VERWALTUNG CONTACTS sheet
#    Row 0 = true headers (Property ID, Property Address, …)
#    Data starts from row 1 onwards
# ────────────────────────────────────────────────────────
print("Reading VERWALTUNG CONTACTS sheet …")
raw = pd.read_excel(EXCEL_PATH, sheet_name="VERWALTUNG CONTACTS", header=None)

# The actual column names live in row 1
col_names = raw.iloc[1].tolist()
# Clean column names
clean_cols = []
for c in col_names:
    s = str(c).strip()
    # Replace the weird arrow character with a plain one
    s = s.replace("\u2192", "->").replace("→", "->")
    clean_cols.append(s)

df = raw.iloc[2:].copy()
df.columns = clean_cols
df = df.dropna(how="all")

# Map the "Unnamed: N" style names from row 0 to friendlier names
rename_map = {
    "Property ID":               "PROPERTY_ID",
    "Property Address":          "PROPERTY_ADDRESS",
    "OWN / SUB":                 "OWN_SUB",
    "Agency / Verwaltung Name":  "AGENCY_NAME",
    "Agency Address":            "AGENCY_ADDRESS",
    "Contact 1 -> Name":         "CONTACT1_NAME",
    "Contact 1 -> Mobile":       "CONTACT1_MOBILE",
    "Contact 1 -> Landline":     "CONTACT1_LANDLINE",
    "Contact 1 -> Email":        "CONTACT1_EMAIL",
    "Contact 2 -> Name":         "CONTACT2_NAME",
    "Contact 2 -> Mobile":       "CONTACT2_MOBILE",
    "Contact 2 -> Landline":     "CONTACT2_LANDLINE",
    "Contact 2 -> Email":        "CONTACT2_EMAIL",
    "Hauswart -> Name":          "HAUSWART_NAME",
    "Hauswart -> Mobile":        "HAUSWART_MOBILE",
    "Hauswart -> Landline / Tel":"HAUSWART_LANDLINE",
    "Hauswart -> Email":         "HAUSWART_EMAIL",
    "Remarks":                   "REMARKS",
}

# The Excel uses a weird bullet/arrow character; let's handle all variants
# by matching on partial strings
new_col_map = {}
for old_col in df.columns:
    matched = False
    for pattern, new_name in rename_map.items():
        if pattern.replace("->", "").strip().lower() in old_col.replace("->", "").replace("→", "").replace("\u2192", "").strip().lower():
            new_col_map[old_col] = new_name
            matched = True
            break
    if not matched:
        new_col_map[old_col] = old_col  # keep as-is

df = df.rename(columns=new_col_map)

# Clean records
records = []
for _, row in df.iterrows():
    rec = {k: clean_val(v) for k, v in row.items()}
    # Skip blank rows (no property ID)
    if rec.get("PROPERTY_ID") is None:
        continue
    records.append(rec)

print(f"  -> {len(records)} records found")

col_vc = db["verwaltung_contacts"]
col_vc.drop_indexes()
col_vc.delete_many({})
if records:
    col_vc.insert_many(records)
    print(f"  [OK] Inserted {len(records)} docs into 'verwaltung_contacts'")
else:
    print("  [WARN]  No records to insert.")


# ────────────────────────────────────────────────────────
# 2. AGENCY SUMMARY sheet
# ────────────────────────────────────────────────────────
print("\nReading AGENCY SUMMARY sheet …")
raw2 = pd.read_excel(EXCEL_PATH, sheet_name="AGENCY SUMMARY", header=None)

agency_cols = raw2.iloc[1].tolist()
clean_agency_cols = [str(c).strip() for c in agency_cols]

df2 = raw2.iloc[2:].copy()
df2.columns = clean_agency_cols
df2 = df2.dropna(how="all")

agency_rename = {
    "#": "RANK",
    "AGENCY / VERWALTUNG": "AGENCY_NAME",
    "PROPERTY COUNT": "PROPERTY_COUNT",
    "PROPERTY IDs": "PROPERTY_IDS",
}
df2 = df2.rename(columns={c: agency_rename.get(c, c) for c in df2.columns})

agency_records = []
for _, row in df2.iterrows():
    rec = {k: clean_val(v) for k, v in row.items()}
    if rec.get("AGENCY_NAME") is None:
        continue
    agency_records.append(rec)

print(f"  -> {len(agency_records)} agency summary records found")

col_as = db["agency_summary"]
col_as.delete_many({})
if agency_records:
    col_as.insert_many(agency_records)
    print(f"  [OK] Inserted {len(agency_records)} docs into 'agency_summary'")
else:
    print("  [WARN]  No records to insert.")

print("\nVerwaltung upload complete.")
client.close()
