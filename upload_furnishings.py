"""
upload_furnishings.py

Reads Furnishings_Inventory_Final-v1.0.xlsx and pushes two collections:

  furnishings_inventory        – one document per property
  furnishings_inventory_schema – one document per column
                                 capturing all 5 header rows from the Excel

Excel layout (0-indexed):
  Row 0 : Category group
  Row 1 : Data type
  Row 2 : Allowed values
  Row 3 : Description
  Row 4 : Field name       <- MongoDB key
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

EXCEL_FILE = "Furnishings_Inventory_Final-v1.0.xlsx"
SHEET_NAME = "FURNISHINGS & INVENTORY"

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

def upload_furnishings():
    print(f"Reading {EXCEL_FILE} (Sheet: {SHEET_NAME}) …")
    raw = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME, header=None)

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
    df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME, header=None, skiprows=5)
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

    # Drop and re-create furnishings_inventory
    print("Dropping 'furnishings_inventory' ...")
    db["furnishings_inventory"].drop()
    if records:
        db["furnishings_inventory"].insert_many(records)
        print(f"[OK] Inserted {len(records)} records into 'furnishings_inventory'")

    # Drop and re-create furnishings_inventory_schema
    print("Dropping 'furnishings_inventory_schema' ...")
    db["furnishings_inventory_schema"].drop()
    if schema_records:
        db["furnishings_inventory_schema"].insert_many(schema_records)
        print(f"[OK] Inserted {len(schema_records)} schema docs into 'furnishings_inventory_schema'")

    client.close()
    print("Done.")


if __name__ == "__main__":
    upload_furnishings()
