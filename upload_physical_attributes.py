import pandas as pd
import os
from pymongo import MongoClient
import math

from dotenv import load_dotenv

# Load connection string from .env
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://sinhasrealty:sinhasrealty@sinhasrealty.cqt4cec.mongodb.net/?appName=sinhasrealty")

# First 3 rows of the Excel are metadata rows (not real property data)
METADATA_IDS = ['ALLOWED VALUES', 'DESCRIPTION', 'PROPERTY_ID']

def clean_data(df):
    return df.where(pd.notnull(df), None)

def upload_physical_attributes(filename="PA1_Physical_Attributes_FINAL-3-RS.xlsx"):
    print(f"Reading {filename}...")
    
    # Read with multi-level headers
    df = pd.read_excel(filename, header=[0, 1])
    
    # Flatten headers
    new_cols = []
    for col in df.columns:
        c0, c1 = col[0], col[1]
        c0 = str(c0).strip()
        c1 = str(c1).strip()
        
        # If the sub-column is unnamed or similar, just use the main column name
        if c1.startswith("Unnamed:") or not c1 or c1 == c0:
            new_col = c0
        else:
            # Flatten with separator
            new_col = f"{c0} - {c1}"
            
        new_cols.append(new_col)
        
    df.columns = new_cols
    df = df.dropna(how='all')
    df = clean_data(df)
    
    # ── Remove the metadata rows (first 3 rows are template definitions, not data) ──
    id_col = 'PROPERTY_ID - DATA TYPE'
    if id_col in df.columns:
        before = len(df)
        df = df[~df[id_col].isin(METADATA_IDS)]
        print(f"Skipped {before - len(df)} metadata rows. Real records: {len(df)}")
    
    # Replace any remaining float NaN values
    records = df.to_dict('records')
    for record in records:
        for k, v in record.items():
            if isinstance(v, float) and math.isnan(v):
                record[k] = None
    
    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client['sinharealty']
    collection = db['physical_attributes']
    
    # Clear old data and reload
    print(f"Clearing old data from 'physical_attributes' collection...")
    collection.delete_many({})
    
    if records:
        print(f"Inserting {len(records)} records...")
        collection.insert_many(records)
        print("Upload successful!")
    else:
        print("No records found to insert.")

if __name__ == "__main__":
    upload_physical_attributes()

