"""
upload_physical_attributes.py

Reads PA1_Physical_Attributes_FINAL-3-RS.xlsx and pushes two collections:

  physical_attributes        – one document per property (144 records)
  physical_attributes_schema – one document per column (44 records)
                               capturing all 5 header rows from the Excel

Excel layout (0-indexed):
  Row 0 : Category group   e.g. BUILDING, LIFT, HEATING …
  Row 1 : Data type        e.g. NUMBER, BOOL, SELECT …
  Row 2 : Allowed values   e.g. "Yes / No"
  Row 3 : Description
  Row 4 : Field name       e.g. PROPERTY_ID, BLDG_YEAR_BUILT …  ← MongoDB key
  Row 5+ : Property data
"""

import math
import os

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://sinhasrealty:sinhasrealty@sinhasrealty.cqt4cec.mongodb.net/?appName=sinhasrealty",
)

EXCEL_FILE = "PA1_Physical_Attributes_FINAL-3-RS.xlsx"

# ─── Helper ───────────────────────────────────────────────────────────────────

def _safe(v):
    """Return None for NaN / blank, else a clean string or number."""
    if v is None:
        return None
    try:
        if isinstance(v, float) and math.isnan(v):
            return None
    except Exception:
        pass
    s = str(v).strip()
    return None if s in ("", "nan") else s


def _safe_val(v):
    """Like _safe but keeps numeric types for data records."""
    if v is None:
        return None
    try:
        if isinstance(v, float) and math.isnan(v):
            return None
    except Exception:
        pass
    return v


# ─── Main ─────────────────────────────────────────────────────────────────────

def upload_physical_attributes():
    print(f"Reading {EXCEL_FILE} …")
    raw = pd.read_excel(EXCEL_FILE, header=None)

    # ── 1. Extract the 5 header rows ──────────────────────────────────────────
    row_category   = raw.iloc[0].tolist()   # Row 0: Category group
    row_dtype      = raw.iloc[1].tolist()   # Row 1: Data type
    row_allowed    = raw.iloc[2].tolist()   # Row 2: Allowed values
    row_desc       = raw.iloc[3].tolist()   # Row 3: Description
    row_field      = raw.iloc[4].tolist()   # Row 4: Field names  <- MongoDB keys

    n_cols = len(row_field)
    print(f"  -> {n_cols} columns detected")

    # Forward-fill category (merged cells appear as NaN in subsequent columns)
    current_cat = None
    categories_filled = []
    for v in row_category:
        s = _safe(v)
        if s and s not in ("nan",):
            current_cat = s
        categories_filled.append(current_cat)

    # -- 2. Build schema records ------------------------------------------------
    schema_records = []
    field_names = []
    for i in range(n_cols):
        field = _safe(row_field[i]) or f"COL_{i}"
        field_names.append(field)
        schema_records.append({
            "col_index":      i,
            "field":          field,
            "category":       categories_filled[i],
            "dtype":          _safe(row_dtype[i]),
            "allowed_values": _safe(row_allowed[i]),
            "description":    _safe(row_desc[i]),
        })

    print(f"  -> Schema: {len(schema_records)} column definitions built")

    # -- 3. Read actual property data (rows 5 onwards) -------------------------
    df = pd.read_excel(EXCEL_FILE, header=None, skiprows=5)
    df.columns = field_names
    df = df.dropna(how="all")

    records = []
    for _, row in df.iterrows():
        doc = {}
        for field in field_names:
            doc[field] = _safe_val(row[field])
        records.append(doc)

    print(f"  -> Data: {len(records)} property records ready")

    # -- 4. Push to MongoDB -----------------------------------------------------
    client = MongoClient(MONGO_URI)
    db = client["sinharealty"]

    # Drop and re-create physical_attributes
    print("Dropping 'physical_attributes' ...")
    db["physical_attributes"].drop()
    if records:
        db["physical_attributes"].insert_many(records)
        print(f"[OK] Inserted {len(records)} records into 'physical_attributes'")

    # Drop and re-create physical_attributes_schema
    print("Dropping 'physical_attributes_schema' ...")
    db["physical_attributes_schema"].drop()
    db["physical_attributes_schema"].insert_many(schema_records)
    print(f"[OK] Inserted {len(schema_records)} schema docs into 'physical_attributes_schema'")

    client.close()
    print("Done.")


if __name__ == "__main__":
    upload_physical_attributes()
