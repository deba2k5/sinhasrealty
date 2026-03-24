import os
import pandas as pd
from pymongo import MongoClient
import certifi

# MongoDB Connection
MONGO_URI = os.getenv("MONGO_URI", 'mongodb+srv://sinhasrealty:sinhasrealty@sinhasrealty.cqt4cec.mongodb.net/?appName=sinhasrealty')
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['sinharealty']

filename = "ORIGINAL TOTAL APARTMENTS AND AVAILIBILITY -with details -6.3.26.xlsx"

print(f"Reading file: {filename}")
xls = pd.ExcelFile(filename, engine='openpyxl')

# Use header=0 as standard if they want a flat upload, but we know the actual headers start at row 1.
# I'll use header=1 to get proper column names for the flat insert.
df = pd.read_excel(xls, sheet_name='OCCUPANCY -Apartment', header=1)
# Drop completely empty rows
df = df.dropna(how='all')

# Fill NaN with None for MongoDB compatibility
df = df.where(pd.notnull(df), None)
records = df.to_dict('records')

collection_name = 'sinhasrealty data'

print(f"Uploading {len(records)} flat records into '{collection_name}' collection...")
if records:
    db[collection_name].drop() # Clear old insert if needed
    db[collection_name].insert_many(records)
    print(f"Successfully inserted {len(records)} records into the '{collection_name}' collection in the 'sinharealty' cluster.")
else:
    print("No records found to insert.")
